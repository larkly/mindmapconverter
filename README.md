# Mind Map Converter

## Overview
This project provides a simple Python script (`mindmapconverter.py`) to facilitate the conversion between Freeplane/Freemind XML mind map files (`.mm`) and PlantUML mind map definitions (`.puml`). This enables users to leverage Freeplane/Freemind for visual mind map creation and then convert these maps into a PlantUML format suitable for embedding in documentation, especially in environments that support PlantUML rendering (e.g., GitLab, Confluence, Markdown viewers with Kroki integration).

## Features
- Convert Freeplane/Freemind (`.mm`) to PlantUML (`.puml`).
- Convert PlantUML (`.puml`) to Freeplane/Freemind (`.mm`).
- Command-line interface for easy conversion.

## Installation

### Prerequisites
- Python 3.x

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/mindmapconverter.git
   cd mindmapconverter
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```
## Usage

The script automatically detects the conversion direction based on the input file's extension.

### Converting Freeplane/Freemind to PlantUML

To convert a Freeplane/Freemind `.mm` file to PlantUML, run:

```bash
python mindmapconverter.py input_file.mm > output_file.puml
```

**Example:**
```bash
python mindmapconverter.py my_mindmap.mm > my_mindmap.puml
```

The output will be a PlantUML definition that can be rendered by PlantUML tools.

### Converting PlantUML to Freeplane/Freemind

To convert a PlantUML `.puml` file to Freeplane/Freemind XML, run:

```bash
python mindmapconverter.py input_file.puml > output_file.mm
```

**Example:**
```bash
python mindmapconverter.py my_mindmap.puml > my_mindmap.mm
```

The output will be an XML file compatible with Freeplane/Freemind.

### Important Notes:
- The script prints the converted content to standard output. Use shell redirection (`>`) to save the output to a file.
- The script assumes `.mm` files are Freeplane/Freemind format and `.puml` files are PlantUML format. Any other extension will be treated as PlantUML for conversion to Freeplane/Freemind.

## Contributing
Contributions are welcome! If you have suggestions for improvements, bug reports, or want to add new features, please feel free to:
1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add some feature'`).
5. Push to the branch (`git push origin feature/YourFeature`).
6. Open a Pull Request.

## License
This project is licensed under the [MIT License](LICENSE).
