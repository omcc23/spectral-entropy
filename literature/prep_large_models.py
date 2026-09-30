import sys
from spacy.cli import download

# The languages we need for the overarching analysis
langs = [ "nl", "pl", "fi", "sv"]

def get_model_name(lang, size):
    return f"{lang}_core_news_{size}" if lang != "en" else f"en_core_web_{size}"

for lang in langs:
    success = False
    for size in ["lg"]:
        model = get_model_name(lang, size)
        print(f"Attempting to download {model}...")
        try:
            download(model)
            print(f"✅ Successfully installed {model}")
            success = True
            break
        except SystemExit:
            print(f"Failed to find {model}")
        except Exception as e:
            print(f"Error installing {model}: {e}")
            
    if not success:
        print(f"❌ Could not install any model for '{lang}'")

print("\n--- Model Fetching Complete ---")
