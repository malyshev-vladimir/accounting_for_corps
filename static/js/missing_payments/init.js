import {initToggleRows} from "./toggle_rows.js";
import {initToggleButtons} from "./toggle_rows.js";
import {initSubmitMissingPayments} from "./submit_selected.js";

document.addEventListener("DOMContentLoaded", () => {
    initToggleRows();
    initToggleButtons();
    initSubmitMissingPayments();
});
