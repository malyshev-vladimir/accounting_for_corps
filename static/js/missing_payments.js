document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".toggle-button").forEach(button => {
        button.addEventListener("click", () => {
            const row = button.closest("tr");
            const icon = button.querySelector("i");
            const selectElement = row.querySelector(".amount-select");

            // Toggle row selection
            const isSelected = row.dataset.selected === "true";

            if (isSelected) {
                // Deselect the row
                row.dataset.selected = "false";
                row.classList.remove("table-success");

                // Restore original appearance
                icon.classList.remove("bi-check-circle");
                icon.classList.add("bi-plus-circle");

                button.classList.remove("btn-success");
                button.classList.add("btn-outline-success");

                selectElement.disabled = false;
            } else {
                // Select the row
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

    document.getElementById("missingPaymentsForm").addEventListener("submit", function (e) {
        e.preventDefault();

        const rows = document.querySelectorAll("tr[data-selected='true']");
        const payload = [];

        rows.forEach(row => {
            const email = row.dataset.email;
            const date = row.dataset.date;
            const amount = row.querySelector(".amount-select").value;
            payload.push({email, date, amount});
        });

        if (payload.length === 0) return;

        fetch("/admin/save_missing_payments", {
            method: "POST",
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({transactions: payload})
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                }
            });
    });
});
