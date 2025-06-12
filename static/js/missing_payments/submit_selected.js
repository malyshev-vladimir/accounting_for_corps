export function initSubmitMissingPayments() {
    const form = document.getElementById("missingPaymentsForm");

    if (!form) return;

    form.addEventListener("submit", function (e) {
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
}
