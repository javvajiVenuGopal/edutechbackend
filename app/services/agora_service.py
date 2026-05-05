from agora_token_builder import RtcTokenBuilder
import time
from app.core.agora_config import AGORA_APP_ID, AGORA_APP_CERTIFICATE


def generate_agora_token(channel, uid):

    expire_time = 3600
    current_time = int(time.time())
    privilege_expired_ts = current_time + expire_time

    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID,
        AGORA_APP_CERTIFICATE,
        channel,
        uid,
        1,
        privilege_expired_ts
    )

    return token