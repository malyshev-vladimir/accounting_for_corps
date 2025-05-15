import {create_dropdown_item} from "./dropdown.js";
import {validate_row} from "./row_validation.js";

export function add_expense_row() {
    const container = document.getElementById("expenses-table-grid");
    if (!container) return console.error("Container #expenses-table-grid not found");

    const unique_id = `file-${Date.now()}`;
    const row = document.createElement("div");
    row.className = "expense-row responsive-row";
    row.innerHTML = `
        <div class="row g-0 flex-wrap">
            <div class="col-12 col-md description-col mb-2 mb-md-0 pe-md-2">
                <div class="input-group">
                    <input type="text" name="description[]" class="form-control description-input" placeholder="Bezeichnung / Grund">
                    <button type="button" class="btn btn-outline-secondary dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false"></button>
                    <ul class="dropdown-menu popular-options"></ul>
                </div>
            </div>
            <div class="col-auto pe-2">
                <input type="text" name="date[]" class="form-control date-input" style="width: 120px;" placeholder="TT.MM.JJJJ">
            </div>
            <div class="col-auto pe-2">
                <input type="number" step="0.01" name="amount[]" class="form-control amount-input" style="width: 100px;" placeholder="€">
            </div>
            <div class="col-auto pe-2">
                <label for="${unique_id}" class="file-btn" title="Attach file"><i class="bi bi-paperclip"></i></label>
                <input type="file" id="${unique_id}" name="receipt[]" class="d-none receipt-input" accept="application/pdf,image/*" onchange="validate_row(this)">
            </div>
            <div class="col-auto">
                <button type="button" class="delete-btn" onclick="remove_row(this)" title="Delete row"><i class="bi bi-x-lg"></i></button>
            </div>
        </div>`;

    const dropdown = row.querySelector(".popular-options");
    const popular_descriptions = ["Fahrtkosten", "Getränke", "Veranstaltungsausgaben", "Materialkosten", "Büromaterial"];
    popular_descriptions.forEach(desc => dropdown.appendChild(create_dropdown_item(desc, row)));

    container.appendChild(row);

    flatpickr(row.querySelector(".date-input"), {
        dateFormat: "d.m.Y",
        allowInput: true,
        disableMobile: true
    });
}

export function remove_row(button) {
    button.closest(".expense-row")?.remove();
    update_total();
}