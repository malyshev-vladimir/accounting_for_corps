export function setupRowToggles() {
    document.querySelectorAll(".header-dark, .card-header.bg-dark").forEach(header => {
        header.addEventListener("click", () => {
            const cardBody = header.nextElementSibling;
            if (cardBody) cardBody.classList.toggle("d-none");
        });
    });

    window.toggleRow = function (toggleElement) {
        const type = toggleElement.dataset.type;
        const key = toggleElement.dataset.key;

        if (!type || !key) return;

        const cells = document.querySelectorAll(`[data-${type}="${key}"]`);
        const collapsed = toggleElement.classList.toggle("collapsed-cell");

        const label = toggleElement.querySelector(".row-label");
        if (label) label.classList.toggle("collapsed-text");

        cells.forEach(cell => {
            cell.classList.toggle("collapsed-cell");

            const input = cell.querySelector("input");
            if (input) input.style.visibility = collapsed ? "hidden" : "visible";

            const span = cell.querySelector("span");
            if (span) span.style.visibility = collapsed ? "hidden" : "visible";
        });
    };
}