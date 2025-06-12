export function initToggleRows() {
    // Hide all but last 2 table-success rows for each card
    document.querySelectorAll(".card-body").forEach(cardBody => {
        const rows = Array.from(cardBody.querySelectorAll("tr.table-success"));
        if (rows.length <= 2) return;

        for (let i = 0; i < rows.length - 2; i++) {
            rows[i].style.display = "none";
        }
    });

    // Add toggle on card header
    document.querySelectorAll(".card-header").forEach(header => {
        header.style.cursor = "pointer";
        header.addEventListener("click", () => {
            const cardBody = header.nextElementSibling;
            if (!cardBody) return;

            const rows = cardBody.querySelectorAll("tr.table-success");
            rows.forEach(row => {
                row.style.display = (row.style.display === "none") ? "" : "none";
            });
        });
    });
}

export function initToggleButtons() {
    // Activate row selection via the green "+" button
    document.querySelectorAll(".toggle-button").forEach(button => {
        button.addEventListener("click", () => {
            const row = button.closest("tr");
            const icon = button.querySelector("i");
            const selectElement = row.querySelector(".amount-select");
            const isSelected = row.dataset.selected === "true";

            if (isSelected) {
                row.dataset.selected = "false";
                row.classList.remove("table-success");

                icon.classList.remove("bi-check-circle");
                icon.classList.add("bi-plus-circle");

                button.classList.remove("btn-success");
                button.classList.add("btn-outline-success");

                selectElement.disabled = false;
            } else {
                row.dataset.selected = "true";
                row.classList.add("table-success");

                icon.classList.remove("bi-plus-circle");
                icon.classList.add("bi-check-circle");

                button.classList.remove("btn-outline-success");
                button.classList.add("btn-success");

                selectElement.disabled = true;
            }
        });
    });
}