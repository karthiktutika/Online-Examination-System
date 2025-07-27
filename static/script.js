/* script.js */
document.addEventListener('DOMContentLoaded', function() {
    // Timer functionality for exams
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        let timeLeft = parseInt(timerElement.getAttribute('data-time'));
        
        const timerInterval = setInterval(function() {
            timeLeft--;
            
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            
            timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            if (timeLeft <= 0) {
                clearInterval(timerInterval);
                alert('Time is up! Your exam will be submitted automatically.');
                document.getElementById('exam-form').submit();
            }
        }, 1000);
    }
    
    // Flash message auto-hide
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.style.display = 'none';
            }, 500);
        }, 5000);
    });
});