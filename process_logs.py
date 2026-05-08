import re
import csv
import os

input_file = r"m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\Log file feltöltés 2026-05-08.txt"
output_file = r"m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\processed_logs.csv"

# Pattern to match rclone log lines
# 2026/05/08 07:55:14 INFO  : 2014/05/p1230091.jpg: Copied (new)
pattern = re.compile(r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} INFO\s+:\s+(.*?):\s+(.*)$')

results = []

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
    exit(1)

with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        match = pattern.match(line.strip())
        if match:
            path = match.group(1)
            status = match.group(2)
            
            # Skip lines that are just summaries or empty
            if not path or path == "There was nothing to transfer":
                continue
                
            # Split path into directory and filename
            if '/' in path:
                directory, filename = path.rsplit('/', 1)
                directory = directory + '/'
            elif '\\' in path:
                directory, filename = path.rsplit('\\', 1)
                directory = directory + '\\'
            else:
                directory = ""
                filename = path
            
            # Determine if uploaded
            # "Copied (new)" definitely means uploaded.
            # "Updated modification time" means only metadata changed.
            uploaded = "Igen" if "Copied (new)" in status else "Nem"
            
            results.append({
                "file név": filename,
                "könyvtár": directory,
                "skip or copy": status,
                "feltöltötte-e a b2-re": uploaded
            })

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=["file név", "könyvtár", "skip or copy", "feltöltötte-e a b2-re"])
    writer.writeheader()
    writer.writerows(results)

print(f"Successfully processed {len(results)} lines.")
print(f"Results saved to: processed_logs.csv")
