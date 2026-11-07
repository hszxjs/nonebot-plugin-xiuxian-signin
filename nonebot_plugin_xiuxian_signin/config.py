from typing import Optional

from pydantic import BaseModel, Field


class Config(BaseModel):
    xiuxian_signin_data_dir: Optional[str] = Field(default=None)
    xiuxian_signin_timezone: str = Field(default="Asia/Shanghai")
    xiuxian_signin_image_width: int = Field(default=900)
    xiuxian_signin_avatar_timeout: float = Field(default=8.0)
    xiuxian_signin_font_path: Optional[str] = Field(default=None)
    xiuxian_signin_bold_font_path: Optional[str] = Field(default=None)
    xiuxian_signin_admin_enabled: bool = Field(default=True)
    xiuxian_signin_admin_token: Optional[str] = Field(default=None)
    xiuxian_signin_admin_path: str = Field(default="/xiuxian-admin")
    xiuxian_signin_admin_host: str = Field(default="0.0.0.0")
    xiuxian_signin_admin_port: int = Field(default=8081)
    # 秘境背景图体积太大不进 wheel（R-09），首次启动按需下载。
    # asset_url 可指向自建镜像或本地 zip；留空用内置的 GitHub Release 地址。
    xiuxian_signin_asset_url: Optional[str] = Field(default=None)
    xiuxian_signin_asset_auto_download: bool = Field(default=True)
    # 存储后端（R-16）：sqlite（默认，WAL）| json（旧实现，应急回退）。
    # 首次以 sqlite 启动且数据目录里有旧 JSON 存档时自动迁移，
    # 原文件改名 *.migrated.bak 保留（切回 json 前手工改回原名即可）。
    xiuxian_signin_storage_backend: str = Field(default="sqlite")
