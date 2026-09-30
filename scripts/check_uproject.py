#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_uproject.py — статическая проверка Unreal-проекта без движка.

ЗАЧЕМ. Этот проект нельзя собрать в CI: Unreal Engine 5.8 занимает
около 100 ГБ, и GitHub Actions его не поставит. Отсюда temptation
объявить проверку невозможной. Но код проверяется без движка — не на
компиляцию, а на согласованность, и ломается чаще всего именно она:

  * заголовок объявляет UCLASS/USTRUCT/UENUM, а «X.generated.h» не
    включён или не последний — UHT не сгенерирует код;
  * код использует модуль, которого нет в Build.cs — «module not found»;
  * код использует плагин, выключенный в .uproject;
  * заголовок существует, но никто его не включает — мёртвый код;
  * в .uproject нет плагина, который Build.cs требует.

ЧТО ПРОВЕРКА НЕ ДЕЛАЕТ И НЕ ДОЛЖНА. Она не ищет «потерянные»
#include. Заголовки движка — CoreMinimal.h, Components/CapsuleComponent.h,
StateTreeTaskBase.h — приходят из установленного UE и в репозитории их
нет по построению. Первая версия этой проверки считала их отсутствующими
и выдала 236 расхождений, из которых полезных не было ни одного. Без
движка нельзя отличить «сломанный include» от «include движка», поэтому
этот класс ошибок здесь просто не ловится — и это сказано в выводе,
а не спрятано.

ЗАПУСК:  python scripts\\check_uproject.py [корень-проекта]
КОД:     0 — всё сошлось; 1 — есть расхождения
"""
import io
import json
import os
import re
import sys

for _s in ("stdout", "stderr"):
    try:
        getattr(sys, _s).reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INC = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
U_MACRO = re.compile(r'^\s*(UCLASS|USTRUCT|UENUM)\b', re.M)
DECL = re.compile(r'^\s*(?:UCLASS|USTRUCT|UENUM|class|struct)\s+\w*\s*'
                  r'([A-Z]\w*)\s*[:{]', re.M)

# Заголовок движка -> модуль, который обязан быть в Build.cs.
MODULE_OF_HEADER = {
    "StateTree": "StateTreeModule",
    "EnvironmentQuery": "AIModule",
    "AIController": "AIModule",
    "BehaviorTree": "AIModule",
    "NavSystem": "NavigationSystem",
    "EnhancedInput": "EnhancedInput",
    "InputAction": "EnhancedInput",
    "InputMappingContext": "EnhancedInput",
    "Components/": "Engine",
    "Camera/": "Engine",
    "GameFramework/": "Engine",
    "Engine/": "Engine",
    "Kismet/": "Engine",
    "Widgets/": "UMG",
    "Blueprint/": "UMG",
    "Slate": "Slate",
    "CoreMinimal": "Core",
    "UObject/": "CoreUObject",
    "Modules/": "Core",
    "Logging/": "Core",
    "Animation/": "Engine",
    "PhysicsEngine/": "PhysicsCore",
    "TimerManager": "Engine",
    "CollisionQueryParams": "Engine",
    "CollisionQueryParams.h": "Engine",
}
PLUGIN_FOR_MODULE = {
    "StateTreeModule": "StateTree",
    "GameplayStateTreeModule": "GameplayStateTree",
    "ModelingToolsEditorMode": "ModelingToolsEditorMode",
}


def fail(errors, msg):
    errors.append(msg)


def read(path):
    with io.open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    src = os.path.join(root, "Source")
    if not os.path.isdir(src):
        print("каталог Source не найден: %s" % src, file=sys.stderr)
        return 2

    errors = []

    # ── .uproject ────────────────────────────────────────────────────────
    uprojects = [f for f in os.listdir(root) if f.endswith(".uproject")]
    if len(uprojects) != 1:
        fail(errors, "ожидался ровно один .uproject, найдено: %d" % len(uprojects))
        up = {}
        upname = "?"
    else:
        upname = uprojects[0]
        try:
            up = json.loads(read(os.path.join(root, upname)))
        except ValueError as e:
            fail(errors, "%s: не разбирается как JSON: %s" % (upname, e))
            up = {}

    enabled_plugins = set(p.get("Name") for p in up.get("Plugins", [])
                          if p.get("Enabled"))
    modules = [m.get("Name") for m in up.get("Modules", [])]

    # ── Build.cs ─────────────────────────────────────────────────────────
    build_cs = None
    for dp, _, fns in os.walk(src):
        found = [f for f in fns if f.endswith(".Build.cs")]
        if found:
            build_cs = os.path.join(dp, found[0])
            break
    if not build_cs:
        fail(errors, "не найден .Build.cs — модуль не соберётся")
        bt = ""
        declared = set()
    else:
        bt = read(build_cs)
        declared = set(re.findall(r'"([A-Za-z0-9_]+)"', bt))

    # модуль .uproject обязан совпадать с каталогом модуля
    mod_dirs = set()
    for entry in os.listdir(src):
        if os.path.isdir(os.path.join(src, entry)):
            mod_dirs.add(entry)
    for m in modules:
        if m and m not in mod_dirs:
            fail(errors, ".uproject объявляет модуль %s, каталога Source/%s нет"
                 % (m, m))

    # ── сбор файлов ─────────────────────────────────────────────────────
    headers, cpps, texts = {}, {}, {}
    for dp, _, fns in os.walk(src):
        for fn in fns:
            p = os.path.join(dp, fn)
            if fn.endswith(".h"):
                headers[fn] = p
            elif fn.endswith(".cpp"):
                cpps[fn] = p
    for name, path in list(headers.items()) + list(cpps.items()):
        texts[name] = read(path)

    needed_modules = set()
    needed_plugins = set()
    included = set()
    declared_types = {}

    for name, text in texts.items():
        for m in DECL.finditer(text):
            declared_types.setdefault(m.group(1), name)

    for name, text in texts.items():
        if name.endswith(".generated.h"):
            continue

        # 1. Рефлексия требует .generated.h, и он должен быть ПОСЛЕДНИМ
        #    include. Это правило UHT; нарушение даёт «generated.h does not
        #    include its own header» или код без сгенерированных свойств.
        if U_MACRO.search(text):
            gen = name[:-2] + ".generated.h"
            if ("%s.generated.h" % name[:-2]) not in text:
                fail(errors,
                     "%s: есть UCLASS/USTRUCT/UENUM, но нет #include \"%s\""
                     % (name, gen))
            else:
                incs = INC.findall(text)
                if gen in incs and incs[-1] != gen:
                    fail(errors,
                         "%s: \"%s\" не последний include — UHT требует его последним"
                         % (name, gen))

        # 2. Используемые модули и плагины
        for inc in INC.findall(text):
            included.add(os.path.basename(inc))
            for key, mod in MODULE_OF_HEADER.items():
                if inc.startswith(key):
                    needed_modules.add(mod)
                    if mod in PLUGIN_FOR_MODULE:
                        needed_plugins.add(PLUGIN_FOR_MODULE[mod])

    # 3. Мёртвые заголовки: объявленный тип, который никто не включает.
    #    В UObject-проекте это почти всегда забытый include, а иногда —
    #    код, который перестал использоваться и тянет зависимости впустую.
    orphan = []
    for tname, fname in declared_types.items():
        if fname.endswith(".generated.h"):
            continue
        if fname in included or fname[:-2] in included:
            continue
        orphan.append("%s (%s)" % (fname, tname))
    if orphan:
        fail(errors, "объявлены, но не включены ниоткуда: %s"
             % ", ".join(sorted(orphan)[:6]))

    # 4. Каждый .cpp должен иметь пару заголовков
    lonely = sorted(c[:-4] + ".h" for c in cpps
                    if (c[:-4] + ".h") not in headers
                    and "Module" not in c)
    if lonely:
        fail(errors, ".cpp без заголовка: %s" % ", ".join(lonely))

    # 5. Зависимости объявлены
    for mod in sorted(needed_modules - declared):
        fail(errors, "код использует модуль %s, его нет в Build.cs" % mod)
    for pl in sorted(needed_plugins - enabled_plugins):
        fail(errors, "код использует плагин %s, он выключен в .uproject" % pl)

    # ── отчёт ───────────────────────────────────────────────────────────
    print("проект:    %s, Engine %s" % (upname, up.get("EngineAssociation", "?")))
    print("модули:    объявлено %d, требуется кодом %d, есть в Build.cs %d"
          % (len(modules), len(needed_modules), len(needed_modules & declared)))
    print("файлы:     заголовков %d, реализаций %d, типов %d"
          % (len([h for h in headers if not h.endswith('.generated.h')]),
             len(cpps), len(declared_types)))
    print("плагины:   включено %s" % (", ".join(sorted(x for x in enabled_plugins if x)) or "нет"))
    print("")
    print("не проверяется: существование заголовков движка. Без установленного")
    print("UE отличить сломанный include от include движка нельзя.")
    print("")

    if errors:
        print("расхождений: %d" % len(errors), file=sys.stderr)
        for e in errors:
            print("  - %s" % e, file=sys.stderr)
        return 1

    print("всё сошлось: рефлексия согласована, зависимости объявлены, "
          "плагины включены, мёртвых заголовков нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
