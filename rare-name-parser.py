import os
import json
import re

NAMES_FOLDER = "Names"

def parse_all_name_files():
    rare_items = set() # Use a set to completely prevent duplicate entries
    
    if not os.path.exists(NAMES_FOLDER):
        print(f"Error: The folder '{NAMES_FOLDER}' does not exist in this directory.")
        return

    # Loop through every file in the Names directory
    for filename in os.listdir(NAMES_FOLDER):
        if filename.endswith(".json"):
            file_path = os.path.join(NAMES_FOLDER, filename)
            print(f"Reading: {filename}...")
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    raw_data = f.read()
                    
                    # Strip out any C-style comments (//) that newserv uses
                    clean_json_str = re.sub(r'//.*', '', raw_data)
                    
                    # Parse the file content
                    item_dict = json.loads(clean_json_str)
                    
                    # Track items in this specific file
                    items_found = 0
                    for code, name in item_dict.items():
                        # Filter for valid strings and true uppercase rares
                        if isinstance(name, str) and name.isupper() and len(name) > 1:
                            # Strip any stray leading/trailing spaces
                            clean_name = name.strip()
                            rare_items.add(clean_name)
                            items_found += 1
                            
                    print(f"  └ Found {items_found} unique rare items.")
                    
            except Exception as e:
                print(f"  ❌ Error parsing {filename}: {e}")

    # Convert back to a sorted list
    final_list = sorted(list(rare_items))
    
    print("\n" + "="*60)
    print(f"🥳 Processing complete! Extracted {len(final_list)} total unique rares across all files.")
    print("="*60 + "\n")
    print("👇 COPY AND PASTE THIS ENTIRE ARRAY INTO YOUR newserv.json 👇\n")
    
    # Format beautifully as a standard JSON array string
    print(json.dumps(final_list, indent=2))

if __name__ == "__main__":
    parse_all_name_files()