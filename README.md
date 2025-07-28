# Understand Your Document

## Project: Intelligent PDF Outline Extractor

This repository contains the solution for Round 1A of the Adobe India Hackathon 2025, focusing on the "Understand Your Document" challenge. The mission is to transform a raw PDF into an intelligent, interactive experience by extracting its structured outline, including the title and hierarchical headings (H1, H2, H3) with their respective page numbers.

## Challenge Theme: Connecting the Dots Through Docs

The core idea behind this challenge is to enable smarter document experiences, such as semantic search, recommendation systems, and insight generation, by making PDF structures understandable to machines.

## Approach

Our solution leverages the `pdfplumber` library for robust PDF parsing and text extraction. The approach involves a multi-stage process:

1.  **Initial Document Analysis:** The script first analyzes the first few pages of the PDF to statistically determine common font sizes and colors. This helps in identifying the body text font size and potential heading font sizes by comparing them to the most frequent text styles.
2.  **Title Extraction:** The document title is identified by looking for the largest font size on the initial pages, assuming it's prominently displayed.
3.  **Line Grouping and Feature Extraction:** Each page's text content is extracted word-by-word, and these words are then intelligently grouped into lines. For each line, critical features such as font size, bold status, color, indentation, and vertical spacing from the previous line are extracted.
4.  **Heuristic Scoring for Headings:** A comprehensive heuristic scoring mechanism is applied to each line. Points are awarded based on:
    * Matching predefined heading font sizes (H1, H2, H3).
    * Boldness of the text.
    * Distinctive font colors (different from common body text colors).
    * Low indentation (closer to the left margin).
    * Significant vertical spacing above the line.
    * Text casing (e.g., ALL CAPS, Title Case).
    * Presence of numbering or outline patterns (e.g., "1. Introduction").
    * Conciseness of the line (fewer words).
    Lines accumulating a score above a certain threshold are classified as headings.
5.  **Hierarchy Assignment:** Based on their font size relative to other identified headings, lines are assigned a hierarchical level (H1, H2, or H3).
6.  **Output Generation:** The extracted title and the list of identified headings, along with their levels and page numbers, are formatted into a JSON output, adhering to the specified format.

## Models or Libraries Used

* **`pdfplumber`**: A Python library for extracting text and data from PDFs. It's used for its ability to extract detailed word attributes like font size, font name, coordinates, and colors, which are crucial for our heuristic-based heading detection.
* **Standard Python Libraries**: `os`, `json`, `re`, `collections` (specifically `defaultdict` and `Counter`) are used for file system operations, JSON formatting, regular expressions, and data aggregation, respectively.

## How to Build and Run Your Solution (Documentation Purpose Only)

This section is for documentation purposes only, as per the hackathon guidelines. Your solution will be built and run using the `docker build` and `docker run` commands specified in the "Expected Execution" section of the challenge brief.

### Prerequisites

* Docker installed on your system.

### Build the Docker Image

Navigate to the root directory of this project where `Dockerfile` is located and run:

```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
