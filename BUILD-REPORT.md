# Build report - Unreal Engine 5.8 Gameplay Kit

- **Date:** 2026-09-30
- **Result:** does not build in CI, and does not pretend to
- **Reason:** Unreal Engine 5.8 is roughly 100 GB and its licence terms do
  not allow putting it on a hosted runner

## What was verified

`scripts/check_uproject.py` runs on every push and passes. It checks the
class of fault that is readable from source and that costs an hour of
building to discover:

- reflection macros without a correctly placed `.generated.h` include
- a module the code uses that `Build.cs` does not declare
- a plugin the code uses that `.uproject` leaves disabled
- a module named in `.uproject` with no directory under `Source/`
- a header nobody includes
- a `.cpp` with no header
- an empty `Content/`
- `Binaries` / `Intermediate` / `Saved` committed by mistake

It found one real fault: `CombatDummy` creates a
`UPhysicsConstraintComponent` and `PhysicsCore` was missing from `Build.cs`,
which fails the build with "Unable to find module PhysicsCore". Fixed.

## What is not verified, and why that is stated rather than hidden

- The engine is not installed, so nothing is compiled.
- `#include` directives are not resolved. Engine headers
  (`CoreMinimal.h`, `Components/CapsuleComponent.h`) live in the installed
  engine and are absent from the repository by construction. Without the
  engine, a broken include cannot be told apart from an engine include.

## Known defect, not fixable here

`Content` holds 753 assets (134 MB) with no `.meta` files. The source
project did not contain them either. Unreal generates them on first open
and assigns **new GUIDs**, so references between assets are already broken
and will change again on the first save.

Before this is sold: open the project in UE 5.8, save every asset, commit
the `.meta` files, verify the references survived. That needs the engine,
and it cannot be done from this repository.
