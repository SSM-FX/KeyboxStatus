import csv
import logging
from pathlib import Path
from requests import get, RequestException
from defusedxml.ElementTree import parse
from cryptography import x509
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)

def fetch_revoked_keybox_list():
    try:
        response = get(
            "https://android.googleapis.com/attestation/status",
            headers={
                "Cache-Control": "max-age=0, no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()["entries"]
    except RequestException as e:
        logging.error(f"Failed to fetch revoked keybox list: {e}")
        raise

def main():
    revoked_keybox_list = fetch_revoked_keybox_list()
    csv_file = Path("status.csv")
    
    # 删除原有的 CSV 文件（如果存在）
    if csv_file.exists():
        csv_file.unlink()
        logging.info("Deleted existing status.csv file.")

    with csv_file.open("w", newline='') as csvfile:
        fieldnames = ["File", "Status"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        output = []

        for kb in Path(".").glob("*.xml"):
            try:
                values = {}
                values["File"] = kb.name

                root = parse(kb).getroot()
                pem_number = int(root.find(".//NumberOfCertificates").text.strip())
                pem_certificates = [
                    cert.text.strip()
                    for cert in root.findall('.//Certificate[@format="pem"]')[:pem_number]
                ]
                certificate = x509.load_pem_x509_certificate(pem_certificates[0].encode())
                serial_number = hex(certificate.serial_number)[2:]

                # 检查吊销状态
                if serial_number not in revoked_keybox_list:
                    values["Status"] = "✅"
                    output.append(values)  # 只添加未吊销的条目
                else:
                    logging.info(f"{values['File']} is revoked.")

            except Exception as e:
                logging.error(f"Error processing {kb.name}: {e}")

        writer.writerows(output)
        
        # 写入时间戳
        writer.writerow({"File": "TIME", "Status": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

if __name__ == "__main__":
    main()
