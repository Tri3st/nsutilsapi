"""
Cross-reference logic for the three identity sources of a single application.

Compares by username (case-insensitive).
Returns sets categorised by which sources contain them.
"""

from typing import Dict, List, Any
from .models import Identity, IdentitySource


def cross_reference(application: str) -> Dict[str, Any]:
    """
    Fetch all identities for an application and cross-reference the three sources.
    Returns a dict with categorised lists and a summary.
    """
    def fetch(source: str) -> Dict[str, dict]:
        qs = Identity.objects.filter(application=application, source=source)
        return {
            obj.username.lower(): {
                "username": obj.username,
                "email": obj.email,
                "display_name": obj.display_name,
                "department": obj.department,
            }
            for obj in qs
        }

    users = fetch(IdentitySource.USERS)
    mail = fetch(IdentitySource.MAIL_DIST_LIST)
    ad = fetch(IdentitySource.AD_GROUP)

    all_keys = set(users) | set(mail) | set(ad)

    result: Dict[str, List[dict]] = {
        "in_all": [],
        "only_in_users": [],
        "only_in_mail_dist": [],
        "only_in_ad_group": [],
        "in_users_and_mail": [],
        "in_users_and_ad": [],
        "in_mail_and_ad": [],
    }

    for key in sorted(all_keys):
        in_u = key in users
        in_m = key in mail
        in_a = key in ad

        entry = (users.get(key) or mail.get(key) or ad.get(key)).copy()
        entry["in_users"] = in_u
        entry["in_mail_dist"] = in_m
        entry["in_ad_group"] = in_a

        if in_u and in_m and in_a:
            result["in_all"].append(entry)
        elif in_u and not in_m and not in_a:
            result["only_in_users"].append(entry)
        elif in_m and not in_u and not in_a:
            result["only_in_mail_dist"].append(entry)
        elif in_a and not in_u and not in_m:
            result["only_in_ad_group"].append(entry)
        elif in_u and in_m and not in_a:
            result["in_users_and_mail"].append(entry)
        elif in_u and in_a and not in_m:
            result["in_users_and_ad"].append(entry)
        elif in_m and in_a and not in_u:
            result["in_mail_and_ad"].append(entry)

    result["summary"] = {
        "total_unique": len(all_keys),
        "users_count": len(users),
        "mail_dist_count": len(mail),
        "ad_group_count": len(ad),
        "in_all_count": len(result["in_all"]),
        "discrepancies": len(all_keys) - len(result["in_all"]),
        "sources_loaded": {
            "users": len(users) > 0,
            "mail_dist_list": len(mail) > 0,
            "ad_group": len(ad) > 0,
        },
    }

    return result
