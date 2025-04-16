from urllib.request import urlopen

url = "ftp://ftp.iac.es/pub/pcoffeebreak/cbinfo.txt"
with urlopen(url) as response:
    content = response.read().decode("utf-8")

# Save content as Markdown file
with open("cbinfo.md", "w", encoding="utf-8") as md_file:
    md_file.write(content)

# Optionally print confirmation
print("Content saved to cbinfo.md")