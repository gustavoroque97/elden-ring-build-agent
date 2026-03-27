import csv
import ast
import os
import re
from typing import List

DATA_DIR = "data/elden-ring-data"
OUTPUT_DIR = "data/rag_data"

# Define the targets to parse
TARGET_CSVS = [
    "classes.csv",
    "weapons.csv",
    "armors.csv",
    "talismans.csv",
    "spirits.csv",
    "incantations.csv",
    "ammos.csv",
    "shields.csv",
    "sorceries.csv",
    "ashes.csv"
]

def sanitize_filename(name):
    # Remove invalid characters for Windows filenames
    return re.sub(r'[<>:"/\\|?*]', '', str(name)).strip().replace(' ', '_').lower()

def format_value(key, val_str):
    if not val_str:
        return ""
    
    # Try parsing lists/dicts
    val = val_str
    if val_str.startswith("[") or val_str.startswith("{"):
        try:
            val = ast.literal_eval(val_str)
        except (ValueError, SyntaxError):
            pass
            
    # If it's a list of dicts (like attack, defence, requirements)
    if isinstance(val, list) and all(isinstance(i, dict) for i in val):
        lines: List[str] = []
        for item in val:
            # e.g. {'name': 'Phy', 'amount': 113}
            parts: List[str] = []
            if 'name' in item:
                parts.append(str(item['name']))
            for k, v in item.items():
                if k != 'name':
                    parts.append(f"{k}: {v}")
            lines.append("- " + " | ".join(parts))
        return "\n".join(lines)
        
    # If it's a generic dict
    elif isinstance(val, dict):
        return "\n".join(f"- {k}: {v}" for k, v in val.items())
        
    # If a valid list of non-dicts
    elif isinstance(val, list):
        return ", ".join(map(str, val))
        
    else:
        # Just standard string
        return str(val).strip()

def generate_markdown(row, item_type):
    lines: List[str] = []
    name = row.get("name", "Unknown Item").title()
    lines.append(f"# {name}")
    lines.append(f"**Item Type:** {item_type.title()}")
    
    # Print a few priority fields inline for compactness
    header_fields = []
    if "category" in row and row["category"]:
        header_fields.append(f"**Category:** {row['category']}")
    if "weight" in row and row["weight"]:
        header_fields.append(f"**Weight:** {row['weight']}")
    if "fpCost" in row and row["fpCost"]:
        header_fields.append(f"**FP Cost:** {row['fpCost']}")
        
    if header_fields:
        lines.append(" | ".join(header_fields))
        
    lines.append("")
    
    if "description" in row and row["description"]:
        lines.append(f"**Description:**\n{row['description']}\n")
    
    if "effect" in row and row["effect"]:
        lines.append(f"**Effect:**\n{row['effect']}\n")
    
    # Process other list/dict fields
    skip_fields = {"id", "name", "image", "description", "effect", "category", "weight", "url", "type", "fpCost"}
    for key, val_str in row.items():
        if key in skip_fields or not val_str:
            continue
        
        formatted = format_value(key, val_str)
        if formatted:
            # Capitalize field names like requiredAttributes to Required Attributes
            pretty_key = re.sub(r'([A-Z])', r' \1', str(key)).title()
            
            lines.append(f"**{pretty_key}:**")
            if "\n" in formatted:
                lines.append(formatted)
            else:
                lines.append(formatted)
            lines.append("")
            
    return "\n".join(lines).strip() + "\n"

def process_csv(csv_filename):
    file_path = os.path.join(DATA_DIR, csv_filename)
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Skipping.")
        return 0
        
    # The item type is based on the filename, e.g. weapons.csv -> Weapon
    item_type = csv_filename.replace(".csv", "").rstrip('s').capitalize()
    # Handle classes.csv correctly
    if item_type == "Classe":
        item_type = "Class"
        
    type_dir = os.path.join(OUTPUT_DIR, csv_filename.replace('.csv', ''))
    os.makedirs(type_dir, exist_ok=True)
    
    count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "name" not in row or not row["name"]:
                continue
                
            md_content = generate_markdown(row, item_type)
            safe_name = sanitize_filename(row["name"])
            
            md_path = os.path.join(type_dir, f"{safe_name}.md")
            with open(md_path, "w", encoding="utf-8") as out_f:
                out_f.write(md_content)
            count += 1
            
    print(f"Processed {count} {item_type} items from {csv_filename}")
    return count

def main():
    if not os.path.exists(DATA_DIR):
        print(f"Data directory '{DATA_DIR}' not found. Please run from the project root.")
        return
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = 0
    for target in TARGET_CSVS:
        total += process_csv(target)
        
    print(f"\nTotal items processed to Markdown: {total}")

if __name__ == "__main__":
    main()
