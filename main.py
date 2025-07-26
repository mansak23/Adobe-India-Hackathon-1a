import pdfplumber
import os
import json
import re
from collections import defaultdict, Counter

# Docker-aware input/output
IN_DOCKER = os.path.exists("/app/input") and os.path.exists("/app/output")
INPUT_DIR = "/app/input" if IN_DOCKER else "./input"
OUTPUT_DIR = "/app/output" if IN_DOCKER else "./output"

def group_lines(words, y_tolerance=3):
    lines = defaultdict(list)
    for word in words:
        added = False
        for y in lines:
            if abs(word['top'] - y) <= y_tolerance:
                lines[y].append(word)
                added = True
                break
        if not added:
            lines[word['top']].append(word)
    sorted_lines = sorted(lines.values(), key=lambda line: line[0]['top'])
    return [sorted(line, key=lambda w: w['x0']) for line in sorted_lines]

def is_bold(word):
    font = word.get("fontname", "").lower()
    return "bold" in font or "black" in font or "demi" in font # Added 'demi' as it often indicates bold

def get_color_tuple(word):
    color = word.get("non_stroking_color")
    if isinstance(color, (list, tuple)) and all(isinstance(x, (int, float)) for x in color):
        return tuple(color)
    return None

def extract_outline(pdf_path):
    outline = []
    title = ""
    all_font_sizes = []
    all_colors = []
    
    with pdfplumber.open(pdf_path) as pdf:
        # Analyze first few pages to determine typical font sizes and colors
        for page in pdf.pages[:5]: # Increased analysis to 5 pages for better statistics
            words = page.extract_words(extra_attrs=["size", "non_stroking_color", "fontname"])
            all_font_sizes.extend([w['size'] for w in words if 'size' in w])
            all_colors.extend([get_color_tuple(w) for w in words if get_color_tuple(w)])

        if not all_font_sizes:
            return {"title": "", "outline": []}

        # Determine the most common font size (likely body text)
        body_font_size = Counter(all_font_sizes).most_common(1)[0][0]
        
        # Identify potential heading sizes - larger than body, sorted descending
        # Increased the range to identify more distinct heading sizes
        potential_heading_sizes = sorted(list(set(s for s in all_font_sizes if s > body_font_size)), reverse=True)
        
        # Map up to top 3 largest unique font sizes to H1, H2, H3
        heading_sizes = potential_heading_sizes[:3]
        size_to_level = {size: f"H{i+1}" for i, size in enumerate(heading_sizes)}
        
        # Determine common text colors to differentiate from heading colors
        common_colors = [color for color, _ in Counter(all_colors).most_common(5)] # Increased to top 5 common colors

        # Attempt to find the title from the first few pages based on largest font size
        # Refined title extraction to consider lines with the largest font size
        for page_idx in range(min(2, len(pdf.pages))): # Check only first 2 pages for title
            page = pdf.pages[page_idx]
            words = page.extract_words(extra_attrs=["size"])
            lines = group_lines(words)
            
            for line in lines:
                if not line:
                    continue
                first_word = line[0]
                font_size = first_word.get("size")
                full_text = " ".join(w['text'] for w in line).strip()
                
                # Title is typically the largest font on the first page, not just largest heading
                if potential_heading_sizes and font_size == potential_heading_sizes[0] and len(full_text) < 100:
                    title = full_text
                    break
            if title:
                break

        # Process each page to extract headings
        for page_num, page in enumerate(pdf.pages):
            words = page.extract_words(extra_attrs=["size", "fontname", "non_stroking_color"])
            lines = group_lines(words)

            # Calculate average line gap for the current page to better detect breaks
            line_gaps = []
            for i in range(1, len(lines)):
                top = lines[i][0]['top']
                prev_bottom = lines[i - 1][-1]['bottom']
                gap = top - prev_bottom
                if gap > 0:
                    line_gaps.append(gap)
            avg_body_gap = sum(line_gaps) / len(line_gaps) if line_gaps else 5 # Default gap if no lines or division by zero

            for i, line in enumerate(lines):
                if not line:
                    continue

                first_word = line[0]
                font_size = first_word.get("size", body_font_size)
                font_color = get_color_tuple(first_word)
                indent = first_word.get("x0", 999)
                bold = is_bold(first_word)
                top = first_word.get("top", 0)

                full_text = " ".join(w['text'] for w in line).strip()
                
                # Skip very long lines, likely not headings
                if len(full_text) > 100 or len(full_text) < 3: # Added minimum length
                    continue

                # Calculate gap above the current line
                gap_above = 0
                if i > 0:
                    prev_bottom = lines[i - 1][-1]['bottom']
                    gap_above = top - prev_bottom
                
                # Heuristic scoring for heading identification
                score = 0
                
                # Check font size hierarchy
                if font_size in heading_sizes:
                    score += 3 if font_size == heading_sizes[0] else (2 if font_size == heading_sizes[1] else 1)
                
                # Boldness is a strong indicator
                if bold:
                    score += 2
                
                # Different color from common body text
                if font_color and font_color not in common_colors:
                    score += 1

                # Indentation (less indented means more likely a heading)
                if indent < 70: # A more generous indentation check
                    score += 1
                
                # Significant vertical spacing above
                if gap_above > (avg_body_gap * 1.5): # A more robust check for gap
                    score += 1
                    
                # All caps or Title Case
                if full_text.isupper() and len(full_text) < 50: # Avoid very long all-caps lines
                    score += 1.5
                elif full_text.istitle() and not (full_text.lower().startswith("the ") or full_text.lower().startswith("a ")): # Check for actual title case, not just first word capitalized
                    score += 1

                # Numbered headings (e.g., 1. Introduction)
                if re.match(r"^\d+(\.\d+)*\s+[A-Za-z]", full_text):
                    score += 2 # Strong indicator

                # If the line is short and has a decent score, it's likely a heading
                if len(line) <= 5 and score >= 3: # Fewer words means more likely a heading if other conditions met
                    score += 1

                # Final decision threshold for a line to be a heading
                if score >= 4: # Adjusted threshold for better precision
                    level = "H3" # Default to H3 if size not in top 3
                    if font_size in size_to_level:
                        level = size_to_level[font_size]
                    else:
                        # If font size is not directly mapped, but it's larger than body and bold, try to assign a level
                        if font_size > body_font_size and bold:
                            if font_size >= heading_sizes[0]: level = "H1"
                            elif len(heading_sizes) > 1 and font_size >= heading_sizes[1]: level = "H2"
                            else: level = "H3"


                    # Prevent adding duplicate headings or very similar ones if already added recently
                    if not outline or (full_text.lower() != outline[-1]['text'].lower() and not full_text.lower().startswith(outline[-1]['text'].lower())):
                        outline.append({
                            "level": level,
                            "text": full_text,
                            "page": page_num + 1
                        })

    return {
        "title": title.strip(),
        "outline": outline
    }

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # dummy PDF for testing
    
    dummy_pdf_content = {
        "title": "ADOBE INDIA HACKATHON: CONNECTING THE DOTS...",
        "outline": [
            {"level": "H1", "text": "Welcome to the \"Connecting the Dots\" Challenge", "page": 2},
            {"level": "H2", "text": "Rethink Reading. Rediscover Knowledge", "page": 2},
            {"level": "H3", "text": "The Journey Ahead", "page": 2},
            {"level": "H3", "text": "Why This Matters", "page": 2},
            {"level": "H1", "text": "Round 1A: Understand Your Document", "page": 3},
            {"level": "H2", "text": "Challenge Theme: Connecting the Dots Through Docs", "page": 3},
            {"level": "H2", "text": "Your Mission", "page": 3},
            {"level": "H2", "text": "Why This Matters", "page": 3},
            {"level": "H2", "text": "What You Need to Build", "page": 3},
            {"level": "H2", "text": "You Will Be Provided", "page": 3},
            {"level": "H2", "text": "Docker Requirements", "page": 4},
            {"level": "H2", "text": "Expected Execution", "page": 4},
            {"level": "H2", "text": "Constraints", "page": 4},
            {"level": "H2", "text": "Scoring Criteria", "page": 5},
            {"level": "H2", "text": "Submission Checklist", "page": 5},
            {"level": "H2", "text": "Pro Tips", "page": 5},
            {"level": "H2", "text": "What Not to Do", "page": 6},
            {"level": "H1", "text": "Round 1B: Persona-Driven Document Intelligence", "page": 7},
            {"level": "H2", "text": "Challenge Brief (For Participants)", "page": 7},
            {"level": "H2", "text": "Input Specification", "page": 7},
            {"level": "H2", "text": "Sample Test Cases", "page": 7},
            {"level": "H2", "text": "Required Output", "page": 8},
            {"level": "H2", "text": "Deliverables", "page": 9},
            {"level": "H2", "text": "Scoring Criteria", "page": 9},
            {"level": "H1", "text": "Appendix:", "page": 10},
        ]
    }

    # Create a dummy PDF file for testing with pdfplumber
    
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
    
   
    for file_name in os.listdir(INPUT_DIR):
        if not file_name.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(INPUT_DIR, file_name)
        
        print(f"Processing {file_name}...")
        result = extract_outline(pdf_path)

        output_file = os.path.join(OUTPUT_DIR, file_name.replace(".pdf", ".json"))
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"✅ Processed: {file_name} → {output_file}")
        print(f"Extracted Outline:\n{json.dumps(result, indent=2, ensure_ascii=False)}") # Print for immediate review


if __name__ == "__main__":
    main()