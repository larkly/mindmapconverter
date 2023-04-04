# mindmapconverter
Converts between Freenode/Freeplane and PlantUML mindmaps

# How to use
This is a simple Python script to convert a Freemind/Freeplane XML file (.mm extension) to PlantUML or in the opposite direction. This allows for using Freemind/Freeplane as a mindmap generator, and converting this to PlantUML when this should be included in markdown documents where PlantUML content can be rendered, for example with Kroki or with native PlantUML support in the markdown renderer (like Gitlab or other tools)

To convert a Freeplane/Freemind file to a PlantUML mindmap, run:

```
python converter.py input_file.mm
```

To convert a PlantUML mindmap to a Freeplane/Freemind XML format, run:

```
python converter.py input_file.puml
```

The script will print the output to the console, which you can then copy and save as the appropriate file format (`.mm` for Freeplane/Freemind or `.puml` for PlantUML). Note that the script assumes that a file with the .mm extension is a Freemind/Freeplane file, and will output PlantUML. Any other file extension will be assumed to be PlantUML that should be converted to Freemind/Freeplane format.

Use standard redirects to store the content directly to a file.

Pull requests are more than welcome.
