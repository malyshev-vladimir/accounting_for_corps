import {mark_field_filled} from "./field_utils.js";
import {update_total} from "./total_calculation.js";

export function validate_row(input) {
    const row = input.closest(".expense-row");
    const desc_input = row.querySelector(".description-input");
    const date_input = row.querySelector(".date-input");
    const amount_input = row.querySelector(".amount-input");
    const file_input = row.querySelector(".receipt-input");
    const file_btn = row.querySelector(".file-btn");

    const desc = desc_input.value.trim();
    const date = date_input.value;
    const amount = amount_input.value;
    const has_receipt = file_input.files.length > 0;

    mark_field_filled(desc_input, !!desc);
    mark_field_filled(date_input, !!date);
    mark_field_filled(amount_input, !!amount);
    file_btn.classList.toggle("filled", has_receipt);

    row.classList.toggle("complete-entry", desc && date && amount && has_receipt);
    update_total();
}
