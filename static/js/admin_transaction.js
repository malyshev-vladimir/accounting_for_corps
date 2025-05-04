function updateDescriptionAndExtras() {
    const type = document.getElementById("type").value;
    const extra = document.getElementById("extra-fields");
    const descInput = document.querySelector("#description-field input");

    extra.innerHTML = "";
    descInput.value = "";

    if (type === "1") {
        descInput.readOnly = false;
    } else {
        descInput.readOnly = true;
        descInput.style.backgroundColor = "#e9ecef";
        descInput.style.cursor = "not-allowed";

        if (type === "2") {
            extra.innerHTML = `
                <label class="form-label mt-2">Datum der Getränkeabrechnung</label>
                <input type="date" name="drinks_report_date" id="drinks_report_date" class="form-control" required>
            `;
            setTimeout(() => {
                const dateInput = document.getElementById("drinks_report_date");
                if (dateInput) {
                    descInput.value = "Getränkeabrechnung von ... ";
                    dateInput.addEventListener("input", () => {
                        const date = dateInput.value;
                        descInput.value = date ? `Getränkeabrechnung vom ${date}` : "Getränkeabrechnung von {date}";
                    });
                }
            }, 0);
        } else if (type === "3") {
            const dateInput = document.getElementById("date_form");
            const dateValue = dateInput?.value;
            const formattedDate = dateValue
                ? (() => {
                    const [yyyy, mm, dd] = dateValue.split("-");
                    return `${dd}.${mm}.${yyyy}`;
                })()
                : "Datum";
            descInput.value = `Gutschrift vom ${formattedDate}`;
        } else if (type === "4") {
            descInput.value = "Strafe ( ... ) von ... ";
            extra.innerHTML = `
                <div class="row mt-3">
                    <div class="col-4">
                        <label class="form-label">Protokollnummer</label>
                        <input type="number" name="protocol_number" id="protocol_number" class="form-control" required>
                    </div>
                    <div class="col-3">
                        <label class="form-label">Protokolltyp</label>
                        <select class="form-select" name="protocol_type" id="protocol_type" required>
                            <option value="AC">AC</option>
                            <option value="CC">CC</option>
                            <option value="GCC">GCC</option>
                            <option value="FCC">FCC</option>
                        </select>
                    </div>
                    <div class="col-4">
                        <label class="form-label">Semester</label>
                        <select class="form-select" name="semester_type" id="semester_type" required>
                            <option value="WiSe">WiSe</option>
                            <option value="SoSe">SoSe</option>
                        </select>
                    </div>
                </div>
            `;
            setTimeout(() => {
                const numberInput = document.getElementById("protocol_number");
                const typeSelect = document.getElementById("protocol_type");
                const semesterSelect = document.getElementById("semester_type");
                const dateInput = document.getElementById("date_form");

                const update = () => {
                    const n = numberInput?.value || "...";
                    const t = typeSelect?.value || "...";
                    const s = semesterSelect?.value || "...";
                    const d = dateInput?.value;
                    const formattedDate = d
                        ? (() => {
                            const [yyyy, mm, dd] = d.split("-");
                            return `${dd}.${mm}.${yyyy}`;
                        })()
                        : "Datum";
                    descInput.value = `Strafe (${n}. ${t} ${s}) vom ${formattedDate}`;
                };

                numberInput?.addEventListener("input", update);
                typeSelect?.addEventListener("change", update);
                semesterSelect?.addEventListener("change", update);
                dateInput?.addEventListener("input", update);

                update();
            }, 0);
        } else if (type === "5") {
            descInput.value = "Rückerstattung (AaA von {date})";
            extra.innerHTML = `
                <label class="form-label mt-2">Datum des Antrags auf Auslagenrückerstattung</label>
                <input type="date" name="refund_request_date" id="refund_request_date" class="form-control" required>
            `;
            setTimeout(() => {
                const dateInput = document.getElementById("refund_request_date");
                if (dateInput) {
                    dateInput.addEventListener("input", () => {
                        const date = dateInput.value;
                        descInput.value = date ? `Rückerstattung (AaA von ${date})` : "Rückerstattung (AaA von {date})";
                    });
                }
            }, 0);
        }
    }
}

function loadTransactions(email) {
    fetch(`/admin/get_transactions?email=${encodeURIComponent(email)}`)
        .then(res => res.json())
        .then(data => {
            const tbody = document.getElementById("transaction-body");
            tbody.innerHTML = "";
            data.forEach((tx) => {
                if (!tx.id) return;
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td style="width: 90px;">${tx.date}</td>
                    <td class="text-center">${tx.amount}</td>
                    <td>${tx.description}</td>
                    <td>
                        <a href="#" class="text-decoration-none text-danger" title="Löschen"
                           onclick="deleteTransaction('${email}', ${tx.id}, this); return false;">
                            <i class="bi bi-trash"></i>
                        </a>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        });
}

function deleteTransaction(email, transactionId) {
    if (!confirm('Are you sure you want to delete this transaction?')) return;
    fetch(`/delete_transaction/${email}/${transactionId}`, { method: 'POST' })
        .then(response => {
            if (response.ok) {
                loadTransactions(email);
            } else {
                response.text().then(text => alert('Error deleting transaction: ' + text));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Network error while deleting.');
        });
}

document.addEventListener("DOMContentLoaded", () => {
    updateDescriptionAndExtras();
    const emailSelect = document.querySelector('select[name="email"]');
    if (emailSelect) {
        loadTransactions(emailSelect.value);
        emailSelect.addEventListener("change", () => {
            loadTransactions(emailSelect.value);
        });
    }
});
