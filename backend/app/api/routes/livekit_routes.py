
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from livekit.api import (
    AccessToken,
    VideoGrants,
    RoomConfiguration,
    RoomAgentDispatch,
)

from app.config import (
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_URL,
)
from app.services.interview_service import interview_service

router = APIRouter(prefix="/api/v1/livekit", tags=["LiveKit"])


class LiveKitTokenRequest(BaseModel):
    session_id: str
    participant_name: str


@router.post("/token")
async def generate_livekit_token(request: LiveKitTokenRequest):
    try:
        interview = await interview_service.get_interview(
            request.session_id
        )

        if not interview:
            raise HTTPException(
                status_code=404,
                detail="Interview session not found",
            )

        if not all([
            LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET,
            LIVEKIT_URL,
        ]):
            raise HTTPException(
                status_code=500,
                detail="LiveKit configuration is missing",
            )

        token = (
            AccessToken(
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET,
            )
            .with_identity(request.participant_name)
            .with_name(request.participant_name)
            .with_grants(
                VideoGrants(
                    room_join=True,
                    room=request.session_id,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .with_room_config(
                RoomConfiguration(
                    agents=[
                        RoomAgentDispatch(
                            agent_name="interview-agent",
                        )
                    ]
                )
            )
        )

        return {
            "token": token.to_jwt(),
            "url": LIVEKIT_URL,
            "room_name": request.session_id,
            "participant_name": request.participant_name,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate LiveKit token",
        )
