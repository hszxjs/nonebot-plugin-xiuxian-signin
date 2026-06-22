from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    xiuxian_signin_data_dir: Optional[str] = Field(default=None)
    xiuxian_signin_timezone: str = Field(default="Asia/Shanghai")
    xiuxian_signin_image_width: int = Field(default=900)
    xiuxian_signin_avatar_timeout: float = Field(default=8.0)
    xiuxian_signin_font_path: Optional[str] = Field(default=None)
    xiuxian_signin_bold_font_path: Optional[str] = Field(default=None)
