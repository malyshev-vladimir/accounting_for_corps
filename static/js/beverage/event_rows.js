let templateCells = [];

export function initializeTemplateReference() {
    const grid = document.getElementById("eventGrid");
    if (!grid) return;

    const allEventCells = Array.from(grid.querySelectorAll(".event-row"));
    const columns = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
    const firstRowLength = columns;

    templateCells = allEventCells.slice(0, firstRowLength).map(cell => cell.cloneNode(true));
}

export function addEventRow() {
    const grid = document.getElementById("eventGrid");
    if (!grid || templateCells.length === 0) return;

    templateCells.forEach(cell => {
        const clone = cell.cloneNode(true);
        const input = clone.querySelector("input");
        if (input) input.value = "";
        const sum = clone.querySelector(".event-sum");
        if (sum) sum.textContent = "0.00";
        grid.appendChild(clone);
    });
}

export function bindRemoveButtons() {
    document.addEventListener("click", event => {
        const btn = event.target.closest(".delete-btn");
        if (btn) {
            removeRow(btn);
        }
    });
}

export function removeRow(button) {
    const grid = document.getElementById("eventGrid");
    const cell = button.closest(".event-row");
    if (!grid || !cell) return;

    const allCells = Array.from(grid.children);
    const columns = getComputedStyle(grid).gridTemplateColumns.split(" ").length;
    const startIndex = allCells.indexOf(cell) - (columns - 1);

    if (startIndex >= 0) {
        for (let i = 0; i < columns; i++) {
            const target = grid.children[startIndex];
            if (target) target.remove();
        }
    }
}
