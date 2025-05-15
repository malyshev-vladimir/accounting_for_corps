import {mark_field_filled} from "./field_utils.js";
import {validate_row} from "./row_validation.js";

export function create_dropdown_item(desc, row) {
    const item = document.createElement("li");
    item.innerHTML = `<a class="dropdown-item" href="#">${desc}</a>`;
    item.querySelector("a").addEventListener("click", () => {
        const input = row.querySelector(".description-input");
        input.value = desc;
        mark_field_filled(input, true);
        validate_row(row.querySelector(".receipt-input"));
    });
    return item;
}
