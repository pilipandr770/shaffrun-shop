document.addEventListener("DOMContentLoaded", () => {
    const assistantForm = document.querySelector("#assistant-form");
    if (!assistantForm) {
        return;
    }

    const inputField = assistantForm.querySelector("textarea");
    const outputContainer = document.querySelector("#assistant-response");

    assistantForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!inputField || !outputContainer) {
            return;
        }

        const question = inputField.value.trim();
        if (!question) {
            return;
        }

        assistantForm.classList.add("is-loading");
        outputContainer.textContent = "Thinking...";

        try {
            const response = await fetch("/assistant/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question })
            });
            const data = await response.json();
            if (data.reply) {
                outputContainer.textContent = data.reply;
            } else {
                outputContainer.textContent = data.error || "Assistant could not respond.";
            }
        } catch (error) {
            console.error(error);
            outputContainer.textContent = "Assistant service is unavailable.";
        } finally {
            assistantForm.classList.remove("is-loading");
        }
    });
});
