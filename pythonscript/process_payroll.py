import csv
import os
import re
import json
from datetime import datetime

def clean_name(name):
    return name.strip().lower()

def format_idr(val):
    return f"{val:,}".replace(",", ".")

def number_to_words(n):
    n = int(n)
    if n == 0:
        return "Nol"
    
    units = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"]
    
    def words(num):
        if num < 12:
            return units[num]
        elif num < 20:
            return units[num - 10] + " Belas"
        elif num < 100:
            return units[num // 10] + " Puluh " + words(num % 10)
        elif num < 200:
            return "Seratus " + words(num - 100)
        elif num < 1000:
            return units[num // 100] + " Ratus " + words(num % 100)
        elif num < 2000:
            return "Seribu " + words(num - 1000)
        elif num < 1000000:
            return words(num // 1000) + " Ribu " + words(num % 1000)
        elif num < 1000000000:
            return words(num // 1000000) + " Juta " + words(num % 1000000)
        return ""
        
    return re.sub(r'\s+', ' ', words(n)).strip()

def process():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    input_dir = os.path.join(base_dir, "datainput")
    cleansing_dir = os.path.join(base_dir, "datacleansing")
    company_dir = os.path.join(base_dir, "companydata")
    history_dir = os.path.join(base_dir, "payrollhistory_log")
    result_dir = os.path.join(base_dir, "result_page")
    
    # 1. Read Company Info
    company_info = {}
    company_file = os.path.join(input_dir, "dataperusahaan.txt")
    if os.path.exists(company_file):
        with open(company_file, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    company_info[k.strip()] = v.strip()
    
    company_name = company_info.get("Nama Perusahaan", "PT. Seduhlur Indo Group")
    company_address = company_info.get("Alamat", "")
    brand = company_info.get("Brand", "Merempah")
    
    # 2. Read raw payroll profiles
    employees = {}
    payroll_raw = []
    payroll_file = os.path.join(input_dir, "data_account_payroll.csv")
    if os.path.exists(payroll_file):
        with open(payroll_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Clean headers and values
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                payroll_raw.append(cleaned_row)
                if cleaned_row.get("Position") == "Allround":
                    emp_name = cleaned_row["Nama"]
                    employees[clean_name(emp_name)] = {
                        "id": cleaned_row.get("ID", ""),
                        "name": emp_name,
                        "position": cleaned_row.get("Position", "Allround"),
                        "bank_account": cleaned_row.get("Bank Account", ""),
                        "platform": cleaned_row.get("Platform", ""),
                        "gaji_bruto": 0,
                        "kasbon_history": [],
                        "kasbon_total": 0
                    }
    
    # Write cleaned employee account database to companydata/
    employee_accounts_file = os.path.join(company_dir, "employee_accounts.csv")
    if payroll_raw:
        with open(employee_accounts_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=payroll_raw[0].keys())
            writer.writeheader()
            writer.writerows(payroll_raw)

    # 3. Read Takehomepay Gaji Bruto
    takehome_raw = []
    takehome_file = os.path.join(input_dir, "data takehomepay.csv")
    if os.path.exists(takehome_file):
        with open(takehome_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                takehome_raw.append(cleaned_row)
                name_key = clean_name(cleaned_row["Nama Pegawai"])
                if name_key in employees:
                    employees[name_key]["gaji_bruto"] = int(cleaned_row["Gaji Bruto (Total)"])

    # Write cleaned takehomepay to datacleansing/
    takehome_clean_file = os.path.join(cleansing_dir, "data_takehomepay_clean.csv")
    if takehome_raw:
        with open(takehome_clean_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=takehome_raw[0].keys())
            writer.writeheader()
            writer.writerows(takehome_raw)

    # 4. Read Kasbon History
    kasbon_raw = []
    kasbon_file = os.path.join(input_dir, "datakasbon.csv")
    if os.path.exists(kasbon_file):
        with open(kasbon_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                kasbon_raw.append(cleaned_row)
                name_key = clean_name(cleaned_row["Nama Pegawai"])
                if name_key in employees:
                    nominal = int(cleaned_row["Nominal Kasbon"])
                    date_str = cleaned_row["Tanggal Pengajuan"].strip()
                    if "-" in date_str and len(date_str) == 10:
                        parts = date_str.split("-")
                        if len(parts[0]) == 4:
                            date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    
                    employees[name_key]["kasbon_history"].append({
                        "tanggal": date_str,
                        "nominal": nominal,
                        "keterangan": "Kasbon Pegawai"
                    })
                    employees[name_key]["kasbon_total"] += nominal

    # Write cleaned kasbon to datacleansing/
    kasbon_clean_file = os.path.join(cleansing_dir, "datakasbon_clean.csv")
    if kasbon_raw:
        with open(kasbon_clean_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=kasbon_raw[0].keys())
            writer.writeheader()
            writer.writerows(kasbon_raw)

    # Calculate net takehomepay
    for name_key, data in employees.items():
        data["net_pay"] = data["gaji_bruto"] - data["kasbon_total"]
        data["terbilang"] = number_to_words(data["net_pay"]) + " Rupiah"
        data["kasbon_history"].sort(key=lambda x: x["tanggal"])

    # 5. Save History Master Log
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_log_file = os.path.join(history_dir, f"payroll_log_{timestamp}.json")
    history_data = {
        "timestamp": datetime.now().isoformat(),
        "employees": {data["name"].upper(): data for data in employees.values()}
    }
    with open(history_log_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=4)

    # 6. Generate JSON to embed in pages
    employees_json = json.dumps({data["name"].upper(): data for data in employees.values()}, indent=4)

    # Write slip_gaji.html
    write_slip_gaji(result_dir, brand, company_name, company_address, employees_json)

    # Write rincian_potongan.html
    write_rincian_potongan(result_dir, brand, company_name, company_address, employees_json)

    # Write rekap_gaji.html
    write_rekap_gaji(result_dir, brand, company_name, company_address, employees, total_bruto=sum(e["gaji_bruto"] for e in employees.values()), total_potongan=sum(e["kasbon_total"] for e in employees.values()), total_net=sum(e["net_pay"] for e in employees.values()))

    print("Success: Payroll processing pipeline executed.")

def write_slip_gaji(result_dir, brand, company_name, company_address, employees_json):
    # (Existing slip_gaji code goes here)
    content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <script>
        if (sessionStorage.getItem('payroll_auth') !== 'true') {{
            window.location.href = '../index.html';
        }}
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Slip Gaji - {brand}</title>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root {{
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --border-color: #000000;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Courier Prime', Courier, monospace;
            background-color: var(--bg-color);
            color: #000000;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 30px 10px;
        }}
        .controls-container {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            width: 100%;
            max-width: 750px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
            justify-content: space-between;
            border: 1px solid #cbd5e1;
        }}
        .control-group {{ display: flex; flex-direction: column; gap: 5px; }}
        label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; }}
        select {{ padding: 8px 12px; font-size: 14px; border-radius: 6px; border: 1px solid #cbd5e1; cursor: pointer; }}
        .btn-download {{ background-color: #0f172a; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; }}
        .btn-download:hover {{ background-color: #1e293b; }}
        .slip-wrapper {{ background-color: var(--card-bg); width: 100%; max-width: 750px; padding: 30px 40px; border: 2px solid var(--border-color); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }}
        .header-section {{ text-align: center; margin-bottom: 12px; }}
        .company-name {{ font-size: 18px; font-weight: 700; text-transform: uppercase; }}
        .company-address {{ font-size: 11px; margin-top: 3px; }}
        .line-double {{ border-top: 1px dashed #000; border-bottom: 1px dashed #000; height: 4px; margin: 8px 0; }}
        .line-single {{ border-top: 1px dashed #000; margin: 8px 0; }}
        .slip-title {{ text-align: center; font-size: 15px; font-weight: 700; text-decoration: underline; }}
        .slip-periode {{ text-align: center; font-size: 12px; margin-bottom: 15px; }}
        .employee-info {{ display: grid; grid-template-columns: auto 1fr; row-gap: 4px; column-gap: 12px; font-size: 13px; margin-bottom: 15px; }}
        .info-label {{ width: 90px; }}
        .financials-container {{ display: grid; grid-template-columns: 1fr 1.05fr; column-gap: 40px; font-size: 12px; }}
        .fin-column {{ display: flex; flex-direction: column; }}
        .section-title {{ font-weight: 700; text-decoration: underline; margin-bottom: 8px; }}
        .fin-table {{ width: 100%; border-collapse: collapse; }}
        .fin-table td {{ padding: 3px 0; }}
        .val-col {{ text-align: right; }}
        .eq-col {{ width: 15px; text-align: center; }}
        .total-row {{ font-weight: 700; }}
        .net-salary-box {{ border: 1px solid #000; margin-top: 15px; padding: 8px 12px; font-size: 13px; text-align: center; }}
        .net-amount {{ font-weight: 700; }}
        .terbilang-text {{ font-style: italic; font-size: 11px; margin-top: 4px; }}
        .kasbon-details-section {{ margin-top: 15px; }}
        .kasbon-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .kasbon-table th, .kasbon-table td {{ border-bottom: 1px dotted #000; padding: 3px 4px; }}
        .kasbon-table th {{ font-weight: 700; border-bottom: 1px dashed #000; }}
        .footer-signatures {{ margin-top: 25px; display: flex; justify-content: space-between; font-size: 12px; }}
        .sig-box {{ text-align: center; width: 200px; }}
        .sig-space {{ height: 45px; }}
        .sig-name {{ font-weight: 700; }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .controls-container {{ display: none; }}
            .slip-wrapper {{ box-shadow: none; border: 2px solid #000; padding: 20px 30px; }}
        }}
    </style>
</head>
<body>
    <div class="controls-container">
        <div class="control-group">
            <label for="employee-select">Pilih Pegawai (Allround)</label>
            <select id="employee-select" onchange="updateSlipData()">
                <!-- Options populated dynamically -->
            </select>
        </div>
        <button class="btn-download" onclick="downloadPDF()">
            Download PDF
        </button>
    </div>

    <div class="slip-wrapper" id="slip-target">
        <div class="header-section">
            <div class="company-name">{company_name}</div>
            <div class="company-address">{company_address} ({brand})</div>
        </div>
        <div class="line-double"></div>
        <div class="slip-title">SLIP GAJI KARYAWAN</div>
        <div class="slip-periode" id="slip-period-text">Periode Juni 2026</div>
        <div class="employee-info">
            <div class="info-label">NIK</div><div>: <span id="info-id">-</span></div>
            <div class="info-label">Nama</div><div>: <span id="info-name">-</span></div>
            <div class="info-label">Jabatan</div><div>: <span id="info-position">-</span></div>
            <div class="info-label">Status</div><div>: Karyawan Harian</div>
        </div>
        <div class="financials-container">
            <div class="fin-column">
                <div class="section-title">Penghasilan</div>
                <table class="fin-table">
                    <tbody id="earnings-rows"></tbody>
                </table>
            </div>
            <div class="fin-column">
                <div class="section-title">Potongan</div>
                <table class="fin-table">
                    <tbody id="deductions-rows"></tbody>
                </table>
            </div>
        </div>
        <div class="net-salary-box">
            <div><span>Penerimaan Bersih = </span><span class="net-amount" id="net-val">Rp 0</span></div>
            <div class="terbilang-text">Terbilang: <span id="terbilang-val">-</span></div>
        </div>
        <div class="kasbon-details-section">
            <div class="section-title" style="font-size: 11px;">Rincian Potongan Gaji (Kasbon)</div>
            <table class="kasbon-table">
                <thead>
                    <tr><th>Tanggal</th><th>Keterangan</th><th class="val-col">Nilai Kasbon</th></tr>
                </thead>
                <tbody id="kasbon-detail-rows"></tbody>
            </table>
        </div>
        <div class="line-single"></div>
        <div class="footer-signatures">
            <div class="sig-box">
                <div>Penerima,</div>
                <div class="sig-space"></div>
                <div class="sig-name" id="sig-emp-name">-</div>
            </div>
            <div class="sig-box">
                <div>Malang, <span id="slip-footer-date">-</span></div>
                <div>Bag. Keuangan</div>
                <div class="sig-space"></div>
                <div class="sig-name">Admin Merempah</div>
            </div>
        </div>
    </div>

    <script>
        const employeesData = {employees_json};
        function formatVal(num) {{ return num.toLocaleString('id-ID'); }}
        const today = new Date();
        const dd = String(today.getDate()).padStart(2, '0');
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const yyyy = today.getFullYear();
        const monthNamesIndo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
        document.getElementById("slip-period-text").textContent = `Periode: ${{monthNamesIndo[today.getMonth()]}} ${{yyyy}}`;
        document.getElementById("slip-footer-date").textContent = `${{dd}} ${{monthNamesIndo[today.getMonth()]}} ${{yyyy}}`;

        const selectEl = document.getElementById("employee-select");
        Object.keys(employeesData).forEach(name => {{
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = `${{name}} (${{employeesData[name].id}})`;
            selectEl.appendChild(opt);
        }});

        function updateSlipData() {{
            const empKey = selectEl.value;
            const emp = employeesData[empKey];
            document.getElementById("info-id").textContent = emp.id;
            document.getElementById("info-name").textContent = emp.name;
            document.getElementById("info-position").textContent = emp.position;
            document.getElementById("sig-emp-name").textContent = emp.name;

            let totalPenghasilan = emp.gaji_bruto;
            document.getElementById("earnings-rows").innerHTML = `
                <tr><td>Gaji Pokok</td><td class="eq-col">=</td><td class="val-col">${{formatVal(emp.gaji_bruto)}}</td></tr>
                <tr class="total-row"><td>Total (A)</td><td class="eq-col">=</td><td class="val-col">${{formatVal(totalPenghasilan)}}</td></tr>
            `;

            let totalPotongan = emp.kasbon_total;
            document.getElementById("deductions-rows").innerHTML = `
                <tr><td>Potongan Kasbon</td><td class="eq-col">=</td><td class="val-col">${{formatVal(emp.kasbon_total)}}</td></tr>
                <tr class="total-row"><td>Total (B)</td><td class="eq-col">=</td><td class="val-col">${{formatVal(totalPotongan)}}</td></tr>
            `;

            document.getElementById("net-val").textContent = "Rp " + formatVal(emp.net_pay);
            document.getElementById("terbilang-val").textContent = emp.terbilang;

            let kasbonHTML = "";
            if (emp.kasbon_history.length > 0) {{
                emp.kasbon_history.forEach(item => {{
                    kasbonHTML += `<tr><td>${{item.tanggal}}</td><td>${{item.keterangan}}</td><td class="val-col">Rp ${{formatVal(item.nominal)}}</td></tr>`;
                }});
            }} else {{
                kasbonHTML = `<tr><td colspan="3" style="text-align: center; color: #888;">Tidak ada potongan kasbon periode ini.</td></tr>`;
            }}
            document.getElementById("kasbon-detail-rows").innerHTML = kasbonHTML;
        }}

        if (selectEl.value) {{ updateSlipData(); }}

        function downloadPDF() {{
            const element = document.getElementById('slip-target');
            const empKey = selectEl.value;
            const opt = {{
                margin: [10, 10, 10, 10],
                filename: `Slip_Gaji_${{empKey}}.pdf`,
                image: {{ type: 'jpeg', quality: 0.98 }},
                html2canvas: {{ scale: 2, useCORS: true }},
                jsPDF: {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
            }};
            html2pdf().from(element).set(opt).save();
        }}
    </script>
</body>
</html>
"""
    with open(os.path.join(result_dir, "slip_gaji.html"), "w", encoding="utf-8") as f:
        f.write(content)

def write_rincian_potongan(result_dir, brand, company_name, company_address, employees_json):
    content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <script>
        if (sessionStorage.getItem('payroll_auth') !== 'true') {{
            window.location.href = '../index.html';
        }}
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rincian Potongan - {brand}</title>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root {{
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --border-color: #000000;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Courier Prime', Courier, monospace;
            background-color: var(--bg-color);
            color: #000000;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 30px 10px;
        }}
        .controls-container {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            width: 100%;
            max-width: 750px;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            align-items: center;
            justify-content: space-between;
            border: 1px solid #cbd5e1;
        }}
        .control-group {{ display: flex; flex-direction: column; gap: 5px; }}
        label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; color: #475569; }}
        select {{ padding: 8px 12px; font-size: 14px; border-radius: 6px; border: 1px solid #cbd5e1; cursor: pointer; }}
        .btn-download {{ background-color: #0f172a; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; }}
        .btn-download:hover {{ background-color: #1e293b; }}
        .slip-wrapper {{ background-color: var(--card-bg); width: 100%; max-width: 750px; padding: 30px 40px; border: 2px solid var(--border-color); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }}
        .header-section {{ text-align: center; margin-bottom: 12px; }}
        .company-name {{ font-size: 18px; font-weight: 700; text-transform: uppercase; }}
        .company-address {{ font-size: 11px; margin-top: 3px; }}
        .line-double {{ border-top: 1px dashed #000; border-bottom: 1px dashed #000; height: 4px; margin: 8px 0; }}
        .line-single {{ border-top: 1px dashed #000; margin: 8px 0; }}
        .slip-title {{ text-align: center; font-size: 15px; font-weight: 700; text-decoration: underline; }}
        .slip-periode {{ text-align: center; font-size: 12px; margin-bottom: 15px; }}
        .employee-info {{ display: grid; grid-template-columns: auto 1fr; row-gap: 4px; column-gap: 12px; font-size: 13px; margin-bottom: 15px; }}
        .info-label {{ width: 90px; }}
        .net-salary-box {{ border: 1px solid #000; margin-top: 15px; padding: 8px 12px; font-size: 13px; text-align: center; }}
        .net-amount {{ font-weight: 700; }}
        .terbilang-text {{ font-style: italic; font-size: 11px; margin-top: 4px; }}
        .kasbon-details-section {{ margin-top: 15px; }}
        .kasbon-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .kasbon-table th, .kasbon-table td {{ border-bottom: 1px dotted #000; padding: 3px 4px; }}
        .kasbon-table th {{ font-weight: 700; border-bottom: 1px dashed #000; }}
        .val-col {{ text-align: right; }}
        .footer-signatures {{ margin-top: 25px; display: flex; justify-content: space-between; font-size: 12px; }}
        .sig-box {{ text-align: center; width: 200px; }}
        .sig-space {{ height: 45px; }}
        .sig-name {{ font-weight: 700; }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .controls-container {{ display: none; }}
            .slip-wrapper {{ box-shadow: none; border: 2px solid #000; padding: 20px 30px; }}
        }}
    </style>
</head>
<body>
    <div class="controls-container">
        <div class="control-group">
            <label for="employee-select">Pilih Pegawai (Allround)</label>
            <select id="employee-select" onchange="updateSlipData()">
                <!-- Options populated dynamically -->
            </select>
        </div>
        <button class="btn-download" onclick="downloadPDF()">
            Download PDF
        </button>
    </div>

    <div class="slip-wrapper" id="slip-target">
        <div class="header-section">
            <div class="company-name">{company_name}</div>
            <div class="company-address">{company_address} ({brand})</div>
        </div>
        <div class="line-double"></div>
        <div class="slip-title">RINCIAN POTONGAN GAJI (KASBON)</div>
        <div class="slip-periode" id="slip-period-text">Periode Juni 2026</div>
        <div class="employee-info">
            <div class="info-label">NIK</div><div>: <span id="info-id">-</span></div>
            <div class="info-label">Nama</div><div>: <span id="info-name">-</span></div>
            <div class="info-label">Jabatan</div><div>: <span id="info-position">-</span></div>
            <div class="info-label">Status</div><div>: Karyawan Harian</div>
        </div>
        <div class="kasbon-details-section">
            <table class="kasbon-table">
                <thead>
                    <tr><th style="width: 100px;">Tanggal</th><th>Keterangan</th><th class="val-col" style="width: 120px;">Nilai Kasbon</th></tr>
                </thead>
                <tbody id="kasbon-detail-rows"></tbody>
            </table>
        </div>
        <div class="net-salary-box">
            <div><span>Total Potongan Kasbon = </span><span class="net-amount" id="net-val">Rp 0</span></div>
            <div class="terbilang-text">Terbilang: <span id="terbilang-val">-</span></div>
        </div>
        <div class="line-single"></div>
        <div class="footer-signatures">
            <div class="sig-box">
                <div>Penerima,</div>
                <div class="sig-space"></div>
                <div class="sig-name" id="sig-emp-name">-</div>
            </div>
            <div class="sig-box">
                <div>Malang, <span id="slip-footer-date">-</span></div>
                <div>Bag. Keuangan</div>
                <div class="sig-space"></div>
                <div class="sig-name">Admin Merempah</div>
            </div>
        </div>
    </div>

    <script>
        const employeesData = {employees_json};
        function formatVal(num) {{ return num.toLocaleString('id-ID'); }}
        
        // Date Setup
        const today = new Date();
        const dd = String(today.getDate()).padStart(2, '0');
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const yyyy = today.getFullYear();
        const monthNamesIndo = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"];
        document.getElementById("slip-period-text").textContent = `Periode: ${{monthNamesIndo[today.getMonth()]}} ${{yyyy}}`;
        document.getElementById("slip-footer-date").textContent = `${{dd}} ${{monthNamesIndo[today.getMonth()]}} ${{yyyy}}`;

        const selectEl = document.getElementById("employee-select");
        Object.keys(employeesData).forEach(name => {{
            const opt = document.createElement("option");
            opt.value = name;
            opt.textContent = `${{name}} (${{employeesData[name].id}})`;
            selectEl.appendChild(opt);
        }});

        function updateSlipData() {{
            const empKey = selectEl.value;
            const emp = employeesData[empKey];
            document.getElementById("info-id").textContent = emp.id;
            document.getElementById("info-name").textContent = emp.name;
            document.getElementById("info-position").textContent = emp.position;
            document.getElementById("sig-emp-name").textContent = emp.name;

            document.getElementById("net-val").textContent = "Rp " + formatVal(emp.kasbon_total);
            
            // Generate Terbilang for deduction
            let totalDeductionVal = emp.kasbon_total;
            let tempTerbilang = "";
            function terbilangJS(nilai) {{
                nilai = Math.floor(Math.abs(nilai));
                const huruf = ["", "Satu", "Dua", "Tiga", "Empat", "Lima", "Enam", "Tujuh", "Delapan", "Sembilan", "Sepuluh", "Sebelas"];
                let temp = "";
                if (nilai < 12) {{ temp = " " + huruf[nilai]; }}
                else if (nilai < 20) {{ temp = terbilangJS(nilai - 10) + " Belas"; }}
                else if (nilai < 100) {{ temp = terbilangJS(nilai / 10) + " Puluh" + terbilangJS(nilai % 10); }}
                else if (nilai < 200) {{ temp = " Seratus" + terbilangJS(nilai - 100); }}
                else if (nilai < 1000) {{ temp = terbilangJS(nilai / 100) + " Ratus" + terbilangJS(nilai % 100); }}
                else if (nilai < 2000) {{ temp = " Seribu" + terbilangJS(nilai - 1000); }}
                else if (nilai < 1000000) {{ temp = terbilangJS(nilai / 1000) + " Ribu" + terbilangJS(nilai % 1000); }}
                else if (nilai < 1000000000) {{ temp = terbilangJS(nilai / 1000000) + " Juta" + terbilangJS(nilai % 1000000); }}
                return temp.trim();
            }}
            document.getElementById("terbilang-val").textContent = totalDeductionVal > 0 ? (terbilangJS(totalDeductionVal) + " Rupiah") : "Nol Rupiah";

            let kasbonHTML = "";
            if (emp.kasbon_history.length > 0) {{
                emp.kasbon_history.forEach(item => {{
                    kasbonHTML += `<tr><td>${{item.tanggal}}</td><td>${{item.keterangan}}</td><td class="val-col">Rp ${{formatVal(item.nominal)}}</td></tr>`;
                }});
            }} else {{
                kasbonHTML = `<tr><td colspan="3" style="text-align: center; color: #888;">Tidak ada potongan kasbon periode ini.</td></tr>`;
            }}
            document.getElementById("kasbon-detail-rows").innerHTML = kasbonHTML;
        }}

        if (selectEl.value) {{ updateSlipData(); }}

        function downloadPDF() {{
            const element = document.getElementById('slip-target');
            const empKey = selectEl.value;
            const opt = {{
                margin: [10, 10, 10, 10],
                filename: `Rincian_Potongan_${{empKey}}.pdf`,
                image: {{ type: 'jpeg', quality: 0.98 }},
                html2canvas: {{ scale: 2, useCORS: true }},
                jsPDF: {{ unit: 'mm', format: 'a4', orientation: 'portrait' }}
            }};
            html2pdf().from(element).set(opt).save();
        }}
    </script>
</body>
</html>
"""
    with open(os.path.join(result_dir, "rincian_potongan.html"), "w", encoding="utf-8") as f:
        f.write(content)

def write_rekap_gaji(result_dir, brand, company_name, company_address, employees, total_bruto, total_potongan, total_net):
    rekap_rows = ""
    individual_slips = ""
    
    # helper
    def py_format_val(num):
        return f"{num:,}".replace(",", ".")

    for i, emp in enumerate(sorted(employees.values(), key=lambda x: x["name"])):
        payroll_acc = f"{emp['platform']} - {emp['bank_account']}"
        rekap_rows += f"""
        <tr>
            <td style="border-bottom: 1px dotted #000; padding: 8px 4px;">{i+1}</td>
            <td style="border-bottom: 1px dotted #000; padding: 8px 4px; font-weight: bold;">{emp['name'].upper()}</td>
            <td style="border-bottom: 1px dotted #000; padding: 8px 4px;" class="val-col">Rp {py_format_val(emp['gaji_bruto'])}</td>
            <td style="border-bottom: 1px dotted #000; padding: 8px 4px;" class="val-col">Rp {py_format_val(emp['kasbon_total'])}</td>
            <td style="border-bottom: 1px dotted #000; padding: 8px 4px;" class="val-col" style="font-weight: bold;">Rp {py_format_val(emp['net_pay'])}</td>
            <td style="border-bottom: 1px dotted #000; padding: 8px 4px;">{payroll_acc}</td>
        </tr>
        """
        
        kasbon_detail_rows = ""
        if emp["kasbon_history"]:
            for item in emp["kasbon_history"]:
                kasbon_detail_rows += f"""
                <tr>
                    <td style="border-bottom: 1px dotted #000; padding: 3px 4px;">{item['tanggal']}</td>
                    <td style="border-bottom: 1px dotted #000; padding: 3px 4px;">{item['keterangan']}</td>
                    <td style="border-bottom: 1px dotted #000; padding: 3px 4px;" class="val-col">Rp {py_format_val(item['nominal'])}</td>
                </tr>
                """
        else:
            kasbon_detail_rows = """
            <tr>
                <td colspan="3" style="text-align: center; color: #888; padding: 6px;">Tidak ada potongan kasbon periode ini.</td>
            </tr>
            """
            
        individual_slips += f"""
        <div class="slip-page-break">
            <div class="slip-wrapper">
                <div class="header-section">
                    <div class="company-name">{company_name}</div>
                    <div class="company-address">{company_address} ({brand})</div>
                </div>
                <div class="line-double"></div>
                <div class="slip-title">SLIP GAJI KARYAWAN</div>
                <div class="slip-periode">Periode Juni 2026</div>
                <div class="employee-info">
                    <div class="info-label">NIK</div><div>: {emp['id']}</div>
                    <div class="info-label">Nama</div><div>: {emp['name'].upper()}</div>
                    <div class="info-label">Jabatan</div><div>: {emp['position']}</div>
                    <div class="info-label">Status</div><div>: Karyawan Harian</div>
                </div>
                <div class="financials-container">
                    <div class="fin-column">
                        <div class="section-title">Penghasilan</div>
                        <table class="fin-table">
                            <tbody>
                                <tr><td>Gaji Pokok</td><td class="eq-col">=</td><td class="val-col">{py_format_val(emp['gaji_bruto'])}</td></tr>
                                <tr class="total-row"><td>Total (A)</td><td class="eq-col">=</td><td class="val-col">{py_format_val(emp['gaji_bruto'])}</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="fin-column">
                        <div class="section-title">Potongan</div>
                        <table class="fin-table">
                            <tbody>
                                <tr><td>Potongan Kasbon</td><td class="eq-col">=</td><td class="val-col">{py_format_val(emp['kasbon_total'])}</td></tr>
                                <tr class="total-row"><td>Total (B)</td><td class="eq-col">=</td><td class="val-col">{py_format_val(emp['kasbon_total'])}</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
                <div class="net-salary-box">
                    <div><span>Penerimaan Bersih = </span><span class="net-amount">Rp {py_format_val(emp['net_pay'])}</span></div>
                    <div class="terbilang-text">Terbilang: {emp['terbilang']}</div>
                </div>
                <div class="kasbon-details-section">
                    <div class="section-title" style="font-size: 11px;">Rincian Potongan Gaji (Kasbon)</div>
                    <table class="kasbon-table">
                        <thead><tr><th>Tanggal</th><th>Keterangan</th><th class="val-col">Nilai Kasbon</th></tr></thead>
                        <tbody>{kasbon_detail_rows}</tbody>
                    </table>
                </div>
                <div class="line-single"></div>
                <div class="footer-signatures">
                    <div class="sig-box">
                        <div>Penerima,</div>
                        <div class="sig-space"></div>
                        <div class="sig-name">{emp['name'].upper()}</div>
                    </div>
                    <div class="sig-box">
                        <div>Malang, 31 Mei 2026</div>
                        <div>Bag. Keuangan</div>
                        <div class="sig-space"></div>
                        <div class="sig-name">Admin Merempah</div>
                    </div>
                </div>
            </div>
        </div>
        """

    content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <script>
        if (sessionStorage.getItem('payroll_auth') !== 'true') {{
            window.location.href = '../index.html';
        }}
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rekapitulasi Gaji - {brand}</title>
    <link href="https://fonts.googleapis.com/css2?family=Courier+Prime:wght@400;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
    <style>
        :root {{
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --border-color: #000000;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Courier Prime', Courier, monospace;
            background-color: var(--bg-color);
            color: #000000;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 30px 10px;
        }}
        .controls-container {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
            width: 100%;
            max-width: 800px;
            margin-bottom: 20px;
            display: flex;
            justify-content: flex-end;
            border: 1px solid #cbd5e1;
        }}
        .btn-download {{ background-color: #0f172a; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 8px; }}
        .btn-download:hover {{ background-color: #1e293b; }}
        .rekap-document {{ width: 100%; max-width: 800px; }}
        .summary-wrapper {{ background-color: var(--card-bg); padding: 30px 40px; border: 2px solid var(--border-color); box-shadow: 0 6px 18px rgba(0,0,0,0.08); margin-bottom: 30px; }}
        .header-section {{ text-align: center; margin-bottom: 12px; }}
        .company-name {{ font-size: 18px; font-weight: 700; text-transform: uppercase; }}
        .company-address {{ font-size: 11px; margin-top: 3px; }}
        .line-double {{ border-top: 1px dashed #000; border-bottom: 1px dashed #000; height: 4px; margin: 8px 0; }}
        .line-single {{ border-top: 1px dashed #000; margin: 8px 0; }}
        .slip-title {{ text-align: center; font-size: 15px; font-weight: 700; text-decoration: underline; }}
        .slip-periode {{ text-align: center; font-size: 12px; margin-bottom: 15px; }}
        .rekap-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 15px; }}
        .rekap-table th {{ font-weight: 700; border-bottom: 1px dashed #000; padding: 8px 4px; }}
        .rekap-table td {{ padding: 8px 4px; }}
        .val-col {{ text-align: right; }}
        .total-row {{ font-weight: 700; border-top: 1px dashed #000; border-bottom: 1px dashed #000; }}
        .slip-wrapper {{ background-color: var(--card-bg); padding: 30px 40px; border: 2px solid var(--border-color); margin-top: 30px; page-break-inside: avoid; }}
        .employee-info {{ display: grid; grid-template-columns: auto 1fr; row-gap: 4px; column-gap: 12px; font-size: 13px; margin-bottom: 15px; }}
        .info-label {{ width: 90px; }}
        .financials-container {{ display: grid; grid-template-columns: 1fr 1.05fr; column-gap: 40px; font-size: 12px; }}
        .fin-column {{ display: flex; flex-direction: column; }}
        .section-title {{ font-weight: 700; text-decoration: underline; margin-bottom: 8px; }}
        .fin-table {{ width: 100%; border-collapse: collapse; }}
        .fin-table td {{ padding: 3px 0; }}
        .eq-col {{ width: 15px; text-align: center; }}
        .net-salary-box {{ border: 1px solid #000; margin-top: 15px; padding: 8px 12px; font-size: 13px; text-align: center; }}
        .net-amount {{ font-weight: 700; }}
        .terbilang-text {{ font-style: italic; font-size: 11px; margin-top: 4px; }}
        .kasbon-details-section {{ margin-top: 15px; }}
        .kasbon-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
        .kasbon-table th, .kasbon-table td {{ border-bottom: 1px dotted #000; padding: 3px 4px; }}
        .kasbon-table th {{ font-weight: 700; border-bottom: 1px dashed #000; }}
        .footer-signatures {{ margin-top: 25px; display: flex; justify-content: space-between; font-size: 12px; }}
        .sig-box {{ text-align: center; width: 200px; }}
        .sig-space {{ height: 45px; }}
        .sig-name {{ font-weight: 700; }}
        .slip-page-break {{ page-break-before: always; }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .controls-container {{ display: none; }}
            .summary-wrapper, .slip-wrapper {{ box-shadow: none; border: 2px solid #000; margin-bottom: 0; }}
        }}
    </style>
</head>
<body>
    <div class="controls-container">
        <button class="btn-download" onclick="downloadPDF()">
            Download PDF Rekapitulasi & Slip
        </button>
    </div>
    <div class="rekap-document" id="rekap-target">
        <div class="summary-wrapper">
            <div class="header-section">
                <div class="company-name">{company_name}</div>
                <div class="company-address">{company_address} ({brand})</div>
            </div>
            <div class="line-double"></div>
            <div class="slip-title">REKAPITULASI TOTAL GAJI PEGAWAI (ALLROUND)</div>
            <div class="slip-periode">Periode Juni 2026</div>
            <table class="rekap-table">
                <thead>
                    <tr><th>No</th><th>Nama Pegawai</th><th class="val-col">Gaji Bruto</th><th class="val-col">Potongan</th><th class="val-col">Net Takehomepay</th><th>Payroll Account</th></tr>
                </thead>
                <tbody>
                    {rekap_rows}
                    <tr class="total-row">
                        <td colspan="2">TOTAL KESELURUHAN</td>
                        <td class="val-col">Rp {py_format_val(total_bruto)}</td>
                        <td class="val-col">Rp {py_format_val(total_potongan)}</td>
                        <td class="val-col">Rp {py_format_val(total_net)}</td>
                        <td>-</td>
                    </tr>
                </tbody>
            </table>
            <div class="line-single"></div>
            <div class="footer-signatures" style="margin-top: 40px;">
                <div class="sig-box" style="margin-left: auto;">
                    <div>Malang, 31 Mei 2026</div><div>Bag. Keuangan</div><div class="sig-space"></div><div class="sig-name">Admin Merempah</div>
                </div>
            </div>
        </div>
        {individual_slips}
    </div>
    <script>
        function downloadPDF() {{
            const element = document.getElementById('rekap-target');
            const opt = {{
                margin: [10, 10, 10, 10],
                filename: `Rekap_Gaji_Mei_2026.pdf`,
                image: {{ type: 'jpeg', quality: 0.98 }},
                html2canvas: {{ scale: 2, useCORS: true }},
                jsPDF: {{ unit: 'mm', format: 'a4', orientation: 'portrait' }},
                pagebreak: {{ mode: ['avoid-all', 'css', 'legacy'] }}
            }};
            html2pdf().from(element).set(opt).save();
        }}
    </script>
</body>
</html>
"""
    with open(os.path.join(result_dir, "rekap_gaji.html"), "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    process()
