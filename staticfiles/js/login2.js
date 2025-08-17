document.getElementById('login-form').addEventListener('submit', function(event) {
    event.preventDefault();
    
    var username = document.getElementById('username').value;
    var password = document.getElementById('password').value;
    var messageElement = document.getElementById('message');
    
    // Simple validation
    if (username === '' || password === '') {
        messageElement.textContent = 'Please enter both username and password';
        return;
    }
    
    // Simple authentication check (in a real app, this would be a server check)
    if (username === 'admin' && password === 'password') {
        messageElement.textContent = 'Login successful!';
        messageElement.style.color = '#388e3c';
        // Redirect or perform other actions on successful login
    } else {
        messageElement.textContent = 'Invalid username or password';
        messageElement.style.color = '#e53935';
    }
});