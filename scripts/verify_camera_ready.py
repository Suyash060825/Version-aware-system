import subprocess
import re

def run_audit():
    # 1. Source TeX checks
    with open("Version_Aware_Ieee_CAMERA_READY.tex") as f:
        tex = f.read()

    checks = {
        "zero ** in tex source": tex.count("**") == 0,
        "zero &#x20; in tex source": tex.count("&#x20;") == 0,
        "zero &# in tex source": tex.count("&#") == 0,
        "zero triple backticks in tex source": tex.count("```") == 0,
        "zero markdown bold (__text__) in tex source": len(re.findall(r"__\w+__", tex)) == 0,
        "zero html entities in tex source": len(re.findall(r"&[a-zA-Z0-9#]+;", tex)) == 0,
    }

    # 2. Extract PDF text
    subprocess.run(["pdftotext", "Version_Aware_Ieee_CAMERA_READY.pdf", "extracted_pdf_camera_ready.txt"], check=True)
    with open("extracted_pdf_camera_ready.txt") as f:
        pdf_text = f.read()

    pages = pdf_text.split("\x0c")
    if pages[-1] == "":
        pages = pages[:-1]

    pdf_checks = {
        "pdf page count is exactly 6": len(pages) == 6,
        "zero ** in pdf text": pdf_text.count("**") == 0,
        "zero &#x20; in pdf text": pdf_text.count("&#x20;") == 0,
        "zero &# in pdf text": pdf_text.count("&#") == 0,
        "zero html entities in pdf text": len(re.findall(r"&[a-zA-Z0-9#]+;", pdf_text)) == 0,
        "zero markdown backticks in pdf text": len(re.findall(r"`[a-zA-Z0-9_]+`", pdf_text)) == 0,
        "references intact (25 citations)": ("R EFERENCES" in pdf_text or "REFERENCES" in pdf_text) and "[25]" in pdf_text,
        "limitations intact (10 items)": ("L IMITATIONS" in pdf_text or "LIMITATIONS" in pdf_text) and "10)" in pdf_text,
        "conclusion intact": ("C ONCLUSION" in pdf_text or "CONCLUSION" in pdf_text),
        "reproducibility statement intact": ("R EPRODUCIBILITY S TATEMENT" in pdf_text or "REPRODUCIBILITY STATEMENT" in pdf_text),
        "biography intact on page 6": "Suyash Pradhan" in pages[5] and "Department of Computer Science" in pages[5],
    }

    print("=== FINAL SOURCE-OF-TRUTH CAMERA-READY AUDIT ===")
    all_passed = True
    for name, passed in {**checks, **pdf_checks}.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"[{status}] {name}")

    print(f"\nOVERALL VERIFICATION RESULT: {'ALL PASS' if all_passed else 'SOME CHECKS FAILED'}")
    return all_passed

if __name__ == "__main__":
    run_audit()
