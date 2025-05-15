import { addEventRow, bindRemoveButtons, initializeTemplateReference } from './event_rows.js';
import { calculateSums } from './beverage_sums.js';
import { setupRowToggles } from './row_toggle.js';

// Wait for DOM to load
document.addEventListener("DOMContentLoaded", () => {
    // Capture a clean template reference for event rows
    initializeTemplateReference();

    // Add two initial empty rows
    addEventRow();
    addEventRow();

    // Bind "+ Veranstaltung" button
    const addBtn = document.getElementById("addEventBtn");
    if (addBtn) {
        addBtn.addEventListener("click", addEventRow);
    }

    // Enable delete buttons
    bindRemoveButtons();

    // Initialize interactivity
    calculateSums();
    setupRowToggles();
});