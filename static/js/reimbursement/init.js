import {add_expense_row, remove_row} from "./add_expense_row.js";
import {mark_field_filled} from "./field_utils.js";
import {validate_row} from "./row_validation.js";

// Export globally if needed for inline HTML calls
window.validate_row = validate_row;
window.remove_row = remove_row;

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('input[name="refund_type"]').forEach(el => {
        el.addEventListener("change", () => {
            const bank_details = document.getElementById("bank-details");
            bank_details.classList.toggle("d-none", el.value !== "bank");
        });
    });

    document.addEventListener("input", event => {
        const name = event.target.name;

        if (["description[]", "date[]", "amount[]"].includes(name)) {
            const receipt = event.target.closest(".expense-row")?.querySelector(".receipt-input");
            if (receipt) validate_row(receipt);
        }

        if (["bank_name", "iban"].includes(name)) {
            mark_field_filled(event.target, !!event.target.value.trim());
        }
    });

    // Add event listener to "+ Neue Zeile" button
    document.getElementById("add-row-btn").addEventListener("click", () => {
        add_expense_row();
    });

    // Initialize with 3 rows
    for (let i = 0; i < 3; i++) add_expense_row();
});
