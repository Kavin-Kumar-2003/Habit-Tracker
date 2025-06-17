document.addEventListener('DOMContentLoaded', function() {
    // Handle habit checkbox changes
    const checkboxes = document.querySelectorAll('.habit-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const habit = this.dataset.habit;
            const day = this.dataset.day;
            const status = this.checked ? 1 : 0;

            // Update the habit status via fetch API
            fetch('/update_habit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    habit: habit,
                    day: day,
                    status: status
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    // If update failed, revert the checkbox
                    this.checked = !this.checked;
                    alert('Failed to update habit status');
                }
            })
            .catch(error => {
                // If error occurs, revert the checkbox
                this.checked = !this.checked;
                console.error('Error updating habit:', error);
            });
        });
    });
});
