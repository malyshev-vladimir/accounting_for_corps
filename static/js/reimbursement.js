// 📌 Предустановленные популярные описания
const popularDescriptions = [
    "Fahrtkosten",
    "Getränke",
    "Veranstaltungsausgaben",
    "Materialkosten",
    "Büromaterial"
];

// 📌 Создаёт одну строку расходов и добавляет её в DOM
function addExpenseRow() {
    const container = document.getElementById("expenses-table-grid");
    if (!container) {
        console.error("Контейнер #expenses-table-grid не найден");
        return;
    }

    const uniqueId = 'file-' + Date.now();

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
                <div class="position-relative">
                    <input type="text" name="date[]" class="form-control date-input" style="width: 120px;" placeholder="TT.MM.JJJJ">
                </div>
            </div>
            <div class="col-auto pe-2">
                <input type="number" step="0.01" name="amount[]" class="form-control amount-input" style="width: 100px;" placeholder="€">
            </div>
            <div class="col-auto pe-2">
                <label for="${uniqueId}" class="file-btn" title="Datei anhängen">
                    <i class="bi bi-paperclip"></i>
                </label>
                <input type="file" id="${uniqueId}" name="receipt[]" class="d-none receipt-input" accept="application/pdf,image/*" onchange="validateRow(this)">
            </div>
            <div class="col-auto">
                <button type="button" class="delete-btn" onclick="removeRow(this)" title="Zeile löschen">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        </div>`;

    const dropdown = row.querySelector(".popular-options");
    popularDescriptions.forEach(desc => {
        const item = document.createElement("li");
        item.innerHTML = `<a class="dropdown-item" href="#">${desc}</a>`;
        item.querySelector("a").addEventListener("click", function () {
            const input = item.closest('.input-group').querySelector(".description-input");
            input.value = desc;
            markFieldFilled(input, true);
            validateRow(row.querySelector(".receipt-input"));
        });
        dropdown.appendChild(item);
    });

    container.appendChild(row);

    const dateInput = row.querySelector(".date-input");
    if (dateInput) {
        flatpickr(dateInput, {
            dateFormat: "d.m.Y",
            allowInput: true,
            position: "auto",
            static: false,
            disableMobile: true
        });
    }
}

// 📌 Удаляет строку расходов
function removeRow(button) {
    button.closest(".expense-row").remove();
    updateTotal();
}

// 📌 Подсвечивает поле при заполнении
function markFieldFilled(input, isFilled) {
    input.classList.toggle("filled", isFilled);
}

// 📌 Валидирует строку и обновляет стиль
function validateRow(input) {
    const file = input.files[0];
    if (file) {
        console.log("Выбран файл:", file.name);
    }

    const row = input.closest(".expense-row");
    const descInput = row.querySelector(".description-input");
    const dateInput = row.querySelector(".date-input");
    const amountInput = row.querySelector(".amount-input");
    const fileBtn = row.querySelector(".file-btn");
    const fileInput = row.querySelector(".receipt-input");

    const desc = descInput.value.trim();
    const date = dateInput.value;
    const amount = amountInput.value;
    const receipt = fileInput.files.length > 0;

    markFieldFilled(descInput, !!desc);
    markFieldFilled(dateInput, !!date);
    markFieldFilled(amountInput, !!amount);

    fileBtn.classList.toggle("filled", receipt);

    if (desc && date && amount && receipt) {
        row.classList.add("complete-entry");
    } else {
        row.classList.remove("complete-entry");
    }

    updateTotal();
}

// 📌 Считает итоговую сумму
function updateTotal() {
    let total = 0;
    const rows = document.querySelectorAll(".expense-row.complete-entry");
    rows.forEach(row => {
        const amount = parseFloat(row.querySelector(".amount-input").value) || 0;
        total += amount;
    });
    document.getElementById("total").textContent = total.toFixed(2);
}

// 📌 После загрузки DOM
document.addEventListener("DOMContentLoaded", () => {
    // Обработчик типа возврата (cc/bank)
    document.querySelectorAll('input[name="refund_type"]').forEach(el => {
        el.addEventListener('change', () => {
            const bankDetails = document.getElementById("bank-details");
            bankDetails.classList.toggle("d-none", el.value !== "bank");
        });
    });

    // Обработка ввода для авто-валидации
    document.addEventListener("input", event => {
        const name = event.target.name;

        if (["description[]", "date[]", "amount[]"].includes(name)) {
            const input = event.target.closest(".expense-row")?.querySelector(".receipt-input");
            if (input) validateRow(input);
        }

        if (["bank_name", "iban"].includes(name)) {
            const value = event.target.value.trim();
            markFieldFilled(event.target, !!value);
        }
    });

    // ✅ Добавляем начальные строки
    addExpenseRow();
    addExpenseRow();
    addExpenseRow();
});
