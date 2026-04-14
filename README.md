# Hospital Sticker Data Extraction

A Python CLI tool that extracts structured patient data from South African hospital admission sticker photos using AI vision.

Trained on sticker formats from:
- **Shelly Beach Private Hospital** (KwaZulu-Natal)
- **Hibiscus Private Hospital Port Shepstone** (KwaZulu-Natal)

## How It Works

1. You photograph a patient admission sticker
2. The tool sends the image to Claude's vision API
3. Claude reads the sticker and returns structured data in 16 standardised fields
4. Results are output as JSON and optionally CSV

## Extracted Fields

| # | Field | Example |
|---|-------|---------|
| 1 | Hospital Name | Shelly Beach Hospital |
| 2 | Patient Number | A34585:2 |
| 3 | Patient Name | John Smith |
| 4 | Ward | SURG |
| 5 | Admitted | 13/03/2025 16:02 |
| 6 | Date of Birth | 06 Dec 1946 |
| 7 | Age | 79Y 3M |
| 8 | Sex | Male |
| 9 | Patient ID | 4612065142182 |
| 10 | Medical Aid & Plan | Discovery Coastal Saver |
| 11 | Med Aid Number | 004713000 |
| 12 | Member Name | Mrs J Smith |
| 13 | Member ID | 4612065142182 |
| 14 | Doctor | Dr D Jones |
| 15 | Phone | 0845167402 |
| 16 | Email | example@email.com |

## Formatting Rules

- **Date of Birth**: Always formatted as `dd Mon yyyy` (e.g. `06 Dec 1946`)
- **Patient Name**: Titles stripped (Mr/Mrs/Ms), reordered to `FirstName Surname`
- **Doctor**: Formatted as `Dr [Initials] [Surname]`
- **Ward**: Just the type — `SURG`, `MED`, `DAY`, `ICU`, etc.
- **Medical Aid & Plan**: Medical aid and scheme combined (e.g. `Gems Non Dental Ruby`)
- **Phone**: Cell number preferred; telephone as fallback

## Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/hospital-sticker-extraction.git
cd hospital-sticker-extraction

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For HEIC support (optional — macOS photos)
pip install pillow-heif

# Set up your API key
cp .env.example .env
# Edit .env and add your Anthropic API key
```

## Usage

### Single image
```bash
python -m extractor.cli sticker_photo.jpg
```

### Multiple images
```bash
python -m extractor.cli photo1.jpg photo2.png photo3.heic
```

### Save to JSON file
```bash
python -m extractor.cli sticker.jpg -o results.json
```

### Export to CSV
```bash
python -m extractor.cli sticker.jpg -o results.json --csv results.csv
```

### Use a different model
```bash
python -m extractor.cli sticker.jpg --model claude-sonnet-4-20250514
```

### Quiet mode (JSON only, no progress output)
```bash
python -m extractor.cli sticker.jpg -q
```

## Example Output

```json
{
  "hospital_name": "Shelly Beach Hospital",
  "patient_number": "A12345:1",
  "patient_name": "John Smith",
  "ward": "SURG",
  "admitted": "15/03/2026 08:30",
  "date_of_birth": "12 Jun 1985",
  "age": "40Y 9M",
  "sex": "Male",
  "patient_id": "7203185047081",
  "medical_aid_and_plan": "Discovery Coastal Saver",
  "med_aid_number": "005839214",
  "member_name": "Mrs J Smith",
  "member_id": "7203185047081",
  "doctor": "Dr D Jones",
  "phone": "0834719258",
  "email": "john.smith@example.com"
}
```

## Supported Hospitals

### Shelly Beach Private Hospital
- Sticker has a top bar: `[PatientNo] [Ward] [BedInfo] [Doctor] Pr:[PracticeNo]`
- Separate `Med. Aid:` and `Med. Scheme:` fields (combined during extraction)
- `Med#:` is the medical aid number

### Hibiscus Private Hospital Port Shepstone
- Different layout with `Scheme:` as combined medical aid field
- `Scheme no:` maps to Med Aid Number
- Doctor format: `Surname (PracticeNo) Initials, DR`

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Privacy

This tool processes sensitive patient data. Ensure you:
- Never commit real patient sticker photos to version control
- Store extracted data securely and in compliance with POPIA
- Only use this tool for authorised medical/administrative purposes
- The `.gitignore` is configured to block image files and output data

## License

MIT
