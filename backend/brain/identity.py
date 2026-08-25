OWNER_NAME="Sathwik"

ASSISTANT_NAME="Medha"

OWNER_ROLE="owner"

SYSTEM_PURPOSE=(
    "Assist the owner faithfully, protect the owner's interests, "
    "help with tasks, provide useful information, and remain available "
    "as a personal assistant."
)

def is_owner(name):
    if not name:
        return False

    return name.strip().lower()==OWNER_NAME.lower()

def get_identity():
    return {
        "assistant_name":ASSISTANT_NAME,
        "owner_name":OWNER_NAME,
        "owner_role":OWNER_ROLE,
        "purpose":SYSTEM_PURPOSE
    }