document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("input.flatpickr").forEach(function (input) {
        flatpickr(input, {
            dateFormat: "d.m.Y",
            allowInput: true,
            locale: "de",
            defaultDate: flatpickr.parseDate(input.value, "d.m.Y"),
            onChange: function (selectedDates) {
                const form = input.closest("form");
                if (!form || !selectedDates[0]) return;

                // Remove previous hidden ISO input if exists
                const existing = form.querySelector("input[type=hidden][name='" + input.name + "']");
                if (existing) existing.remove();

                // Add hidden input with ISO-formatted date
                const hidden = document.createElement("input");
                hidden.type = "hidden";
                hidden.name = input.name;
                hidden.value = selectedDates[0].toISOString().split("T")[0]; // yyyy-mm-dd
                form.appendChild(hidden);

                form.submit();
            }
        });
    });
});