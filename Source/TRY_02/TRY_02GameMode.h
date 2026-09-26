// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "TRY_02GameMode.generated.h"

/**
 *  Simple GameMode for a third person game
 */
UCLASS(abstract)
class ATRY_02GameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	
	/** Constructor */
	ATRY_02GameMode();
};



