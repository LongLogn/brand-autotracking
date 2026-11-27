"""Áp màu và hình của web cho trang đăng nhập Cognito (managed login).

Chạy sau khi stack cognito-demo.yaml đã tạo LoginBranding:
    python infrastructure/cognito-branding/apply_branding.py --stack <tên-stack-auth> --profile <profile> --region ap-southeast-1

Chỉ đổi giao diện; không chạm tới người dùng, client hay cấu hình xác thực.
Managed login chưa hỗ trợ tiếng Việt nên chữ trên trang vẫn là tiếng Anh.
"""
import argparse
import base64
import copy
from pathlib import Path

import boto3

HERE = Path(__file__).resolve().parent
INK, INK_SOFT = "1a2e2aff", "52635eff"
ACTION, ACTION_DARK, ACTION_SOFT = "2448b8ff", "1b3893ff", "e8edfbff"
LINE, PAPER = "c9d1caff", "ffffffff"


def deep_set(target, path, value):
    node = target
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def customize(settings):
    s = copy.deepcopy(settings)
    c, cc, cat = s["components"], s["componentClasses"], s["categories"]
    # Nút chính và phụ theo màu thao tác của web.
    deep_set(c, ["primaryButton", "lightMode"], {
        "defaults": {"backgroundColor": ACTION, "textColor": "ffffffff"},
        "hover": {"backgroundColor": ACTION_DARK, "textColor": "ffffffff"},
        "active": {"backgroundColor": ACTION_DARK, "textColor": "ffffffff"},
        "disabled": c["primaryButton"]["lightMode"]["disabled"],
    })
    deep_set(c, ["secondaryButton", "lightMode"], {
        "defaults": {"backgroundColor": PAPER, "borderColor": LINE, "textColor": INK},
        "hover": {"backgroundColor": "f6f8f5ff", "borderColor": "8a9893ff", "textColor": INK},
        "active": {"backgroundColor": "eef1edff", "borderColor": INK, "textColor": INK},
    })
    # Form trắng bo tròn trên nền xanh thông có họa tiết cột tín hiệu.
    c["form"]["lightMode"] = {"backgroundColor": PAPER, "borderColor": "ffffff00"}
    c["form"]["borderRadius"] = 16.0
    c["form"]["logo"] = {"location": "CENTER", "position": "TOP", "enabled": True, "formInclusion": "IN"}
    c["pageBackground"]["lightMode"] = {"color": "1a2e2aff"}
    c["pageBackground"]["image"] = {"enabled": True}
    c["pageText"]["lightMode"] = {"bodyColor": INK_SOFT, "headingColor": INK, "descriptionColor": INK_SOFT}
    c["alert"]["lightMode"]["error"] = {"backgroundColor": "fcebe9ff", "borderColor": "c8382fff"}
    c["favicon"]["enabledTypes"] = ["SVG"]
    # Ô nhập, liên kết, focus.
    cc["input"]["lightMode"]["defaults"] = {"backgroundColor": PAPER, "borderColor": LINE}
    cc["input"]["borderRadius"] = 8.0
    cc["buttons"]["borderRadius"] = 8.0
    cc["focusState"]["lightMode"] = {"borderColor": ACTION}
    cc["inputLabel"]["lightMode"] = {"textColor": INK}
    if "link" in cc:
        cc["link"]["lightMode"] = {"defaults": {"textColor": ACTION}, "hover": {"textColor": ACTION_DARK}}
    cc["optionControls"]["lightMode"]["selected"] = {"backgroundColor": ACTION, "foregroundColor": "ffffffff"}
    cat["global"]["colorSchemeMode"] = "LIGHT"
    cat["form"]["displayGraphics"] = True
    return s


def asset(category, filename):
    return {"Category": category, "ColorMode": "LIGHT", "Extension": "SVG",
            "Bytes": (HERE / filename).read_bytes()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", required=True)
    parser.add_argument("--profile")
    parser.add_argument("--region", default="ap-southeast-1")
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in
               session.client("cloudformation").describe_stacks(StackName=args.stack)["Stacks"][0]["Outputs"]}
    cognito = session.client("cognito-idp")
    pool, client = outputs["UserPoolId"], outputs["UserPoolClientId"]
    current = cognito.describe_managed_login_branding_by_client(
        UserPoolId=pool, ClientId=client, ReturnMergedResources=True)["ManagedLoginBranding"]
    favicon = asset("FAVICON_SVG", "favicon.svg")
    cognito.update_managed_login_branding(
        UserPoolId=pool, ManagedLoginBrandingId=current["ManagedLoginBrandingId"], UseCognitoProvidedValues=False,
        Settings=customize(current["Settings"]),
        Assets=[asset("PAGE_BACKGROUND", "page-background.svg"), asset("FORM_LOGO", "form-logo.svg"), favicon])
    print(f"Đã áp branding cho client {client}")


if __name__ == "__main__":
    main()
