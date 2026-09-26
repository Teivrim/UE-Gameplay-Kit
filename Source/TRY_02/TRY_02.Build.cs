// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class TRY_02 : ModuleRules
{
	public TRY_02(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"TRY_02",
			"TRY_02/Variant_Platforming",
			"TRY_02/Variant_Platforming/Animation",
			"TRY_02/Variant_Combat",
			"TRY_02/Variant_Combat/AI",
			"TRY_02/Variant_Combat/Animation",
			"TRY_02/Variant_Combat/Gameplay",
			"TRY_02/Variant_Combat/Interfaces",
			"TRY_02/Variant_Combat/UI",
			"TRY_02/Variant_SideScrolling",
			"TRY_02/Variant_SideScrolling/AI",
			"TRY_02/Variant_SideScrolling/Gameplay",
			"TRY_02/Variant_SideScrolling/Interfaces",
			"TRY_02/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
