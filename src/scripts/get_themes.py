import json
import os

themes = []
for theme in os.listdir('src/themes'):
    themes.append(theme)

with open('themes.json', 'w') as theme_file:
    json.dump(themes, theme_file)
