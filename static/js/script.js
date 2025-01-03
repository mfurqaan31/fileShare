// Loading animation
const loadingOverlay = document.querySelector('.loading-overlay');
setTimeout(() => {
    loadingOverlay.style.display = 'none';
}, 2000);

// Initialize DOM elements and variables
const dropZone = document.getElementById('drop-zone');
const fileInput = document.createElement('input');
const uploadPrompt = document.getElementById('uploadPrompt');
const filesList = document.getElementById('filesList');
const filesContainer = filesList.querySelector('.files-container');
const emailForm = document.getElementById('emailForm');
const filesAddedText = document.getElementById('filesAddedText');
const clearAllBtn = document.getElementById('clearAllBtn');
const addMoreFilesBtn = document.getElementById('addMoreFilesBtn');
const emailInput = document.getElementById('emailInput');
const emailTags = document.getElementById('emailTags');
const sendFilesBtn = document.getElementById('sendFilesBtn');
const transferProgress = document.getElementById('transferProgress');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');
const emailVerification = document.getElementById('emailVerification');
const verifyBtn = document.getElementById('verifyBtn');
const otpInputs = document.querySelectorAll('.otp-input');
const verificationSuccess = document.getElementById('verificationSuccess');

fileInput.type = 'file';
fileInput.multiple = true;
fileInput.style.display = 'none';

let files = new Set();
const MAX_TOTAL_SIZE = 1 * 1024 * 1024 * 1024;
let totalSize = 0;
let emails = new Set();

// Format file size for display
function formatFileSize(bytes) {
    if (bytes < 1024) {
        return bytes.toFixed(3) + ' B';
    } else if (bytes < 1048576) {
        return (bytes / 1024).toFixed(3) + ' KB';
    } else if (bytes < 1073741824) {
        return (bytes / 1048576).toFixed(3) + ' MB';
    } else {
        return (bytes / 1073741824).toFixed(3) + ' GB';
    }
}

// Update total size display
function updateTotalSize() {
    filesAddedText.textContent = `${files.size} files added (${formatFileSize(totalSize)})`;
}

// Create file element for display
function createFileElement(file) {
    const fileElement = document.createElement('div');
    fileElement.className = 'file-item';
    
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info';
    const fileName = document.createElement('span');
    fileName.textContent = file.name;
    
    const fileSize = document.createElement('span');
    fileSize.className = 'file-size';
    fileSize.textContent = formatFileSize(file.size);
    
    const removeButton = document.createElement('button');
    removeButton.className = 'remove-file';
    removeButton.innerHTML = '<i class="fa-sharp fa-solid fa-xmark fa-sm" style="color: #cfff04;"></i>';
    removeButton.onclick = () => {
        files.delete(file);
        totalSize -= file.size;
        fileElement.remove();
        updateTotalSize();
        if (files.size === 0) {
            filesList.style.display = 'none';
            uploadPrompt.style.display = 'block';
        }
    };
    
    fileInfo.appendChild(fileName);
    fileInfo.appendChild(fileSize);
    fileElement.appendChild(fileInfo);
    fileElement.appendChild(removeButton);
    
    return fileElement;
}

// Handle file selection
function handleFiles(newFiles) {
    if (newFiles.length === 0) return;
    
    uploadPrompt.style.display = 'none';
    filesList.style.display = 'flex';
    
    Array.from(newFiles).forEach(file => {
        if (!Array.from(files).some(f => f.name === file.name)) {
            files.add(file);
            totalSize += file.size;
            filesContainer.appendChild(createFileElement(file));
        }
    });
    
    updateTotalSize();
}

// Event listeners for file input
dropZone.addEventListener('click', (e) => {
    if (e.target.tagName === 'A') {
        fileInput.click();
    }
});

fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = ''; // Reset input to allow selecting the same file again
});

addMoreFilesBtn.addEventListener('click', () => {
    fileInput.click();
});

clearAllBtn.addEventListener('click', () => {
    files.clear();
    totalSize = 0;
    filesContainer.innerHTML = '';
    updateTotalSize();
    filesList.style.display = 'none';
    uploadPrompt.style.display = 'block';
});

// Email validation
function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Create email tag for display
function createEmailTag(email) {
    const tag = document.createElement('div');
    tag.className = 'email-tag';
    
    const emailText = document.createElement('span');
    emailText.textContent = email;
    emailText.contentEditable = true;
    emailText.addEventListener('blur', () => {
        if (isValidEmail(emailText.textContent)) {
            emails.delete(email);
            emails.add(emailText.textContent);
        } else {
            emailText.textContent = email;
            alert('Please enter a valid email address');
        }
    });
    
    const removeButton = document.createElement('button');
    removeButton.className = 'remove-email';
    removeButton.innerHTML = '<i class="fa-sharp fa-solid fa-xmark fa-sm" style="color: #cfff04;"></i>';
    removeButton.onclick = () => {
        emails.delete(email);
        tag.remove();
        emailInput.style.display = 'block';
    };
    
    tag.appendChild(emailText);
    tag.appendChild(removeButton);
    
    return tag;
}

// Add email to the list
function addEmail(email) {
    if (email && isValidEmail(email) && !emails.has(email)) {
        if (emails.size >= 10) {
            alert('Maximum 10 recipients allowed');
            emailInput.value = '';
            return;
        }

        emails.add(email);
        emailTags.insertBefore(createEmailTag(email), emailInput);
        emailInput.value = '';

        if (emails.size >= 10) {
            emailInput.style.display = 'none';
        }
    } else if (email && !isValidEmail(email)) {
        alert('Please enter a valid email address');
    }
}

// Event listeners for email input
emailInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        addEmail(emailInput.value.trim());
    }
});

emailInput.addEventListener('blur', () => {
    addEmail(emailInput.value.trim());
});

// Send files button click handler
sendFilesBtn.addEventListener('click', () => {
    const fromEmail = document.getElementById('from').value;
    const message = document.getElementById('message').value;
    const privacyCheckbox = document.getElementById('privacyCheckbox');
    
    if (!privacyCheckbox.checked) {
        alert('Please accept the Privacy Policy to continue.');
        return;
    }
    
    if (files.size > 0 && emails.size > 0 && fromEmail) {
        if (totalSize > MAX_TOTAL_SIZE) {
            alert('Total file size exceeds 1 GB limit. Please remove some files.');
            return;
        }

        // Show the OTP verification modal
        emailVerification.style.display = 'block';
        document.querySelector('.file-upload-container').style.display = 'none';

        fetch('/send_otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ from: fromEmail })
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
        })
        .catch(error => {
            alert('Failed to send OTP. Please try again.');
        });
    } else {
        if (files.size == 0) alert('Please add files.');
        if (emails.size == 0) alert('Please add Send to emails.');
        if (!fromEmail) alert('Please add your from email.');
    }
});

// Start file transfer
function startTransfer() {
    transferProgress.style.display = 'flex';
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    formData.append('from', document.getElementById('from').value);
    formData.append('message', document.getElementById('message').value);
    formData.append('recipients', JSON.stringify(Array.from(emails)));

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);
    xhr.timeout = 1800000; // 30 minutes (1800 seconds) timeout

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            const percentComplete = (e.loaded / e.total) * 100;
            progressBar.style.width = percentComplete + '%';
            progressText.textContent = Math.round(percentComplete) + '% Complete';
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            if (response.error) {
                handleTransferError(response.error);
            } else {
                progressBar.style.width = '100%';
                progressText.textContent = '100% Complete - Files uploaded successfully!';
                setTimeout(() => {
                    alert('Transfer complete! Files have been sent to the recipients.');
                    location.reload();
                }, 500);
            }
        } else if (xhr.status === 504) {
            handleTransferError('Gateway timeout error has occurred. The files will take some time to be transferred.', true);
        } else {
            handleTransferError('An error occurred during the transfer. Please try again.');
        }
    };

    xhr.onerror = function() {
        if (xhr.status === 504) {
            handleTransferError('Gateway timeout error has occurred. The files will take some time to be transferred.', true);
        } else {
            handleTransferError('An error occurred during the transfer. Please try again.');
        }
    };

    xhr.ontimeout = function() {
        handleTransferError('Server timeout has occurred. The files will take some time to be transferred.', true);
    };

    xhr.send(formData);
}

// Handle transfer errors
function handleTransferError(errorMessage, isTimeout = false) {
    console.error('Error:', errorMessage);
    
    alert(errorMessage);
    
    // Hide the transfer progress
    transferProgress.style.display = 'none';
    
    // Reload the page after a short delay
        setTimeout(() => {
            location.reload();
        }, 500);
}

// OTP input functionality
otpInputs.forEach((input, index) => {
    input.addEventListener('input', (e) => {
        if (e.inputType === "insertFromPaste") {
            const pastedData = e.target.value;
            for (let i = 0; i < pastedData.length && i < otpInputs.length; i++) {
                otpInputs[i].value = pastedData[i];
            }
            if (otpInputs[otpInputs.length - 1].value) {
                verifyBtn.focus();
            }
        } else {
            const digit = e.target.value.slice(-1);
            input.value = digit;
            if (digit && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            } else if (index === otpInputs.length - 1) {
                verifyBtn.focus();
            }
        }
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Backspace' && index > 0 && input.value.length === 0) {
            otpInputs[index - 1].focus();
        }
    });

    input.addEventListener('paste', (e) => {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text').slice(0, otpInputs.length);
        for (let i = 0; i < pastedData.length; i++) {
            otpInputs[i].value = pastedData[i];
        }
        if (pastedData.length === otpInputs.length) {
            verifyBtn.focus();
        } else {
            otpInputs[pastedData.length].focus();
        }
    });
});

// Verify OTP
verifyBtn.addEventListener('click', () => {
    const otp = Array.from(otpInputs).map(input => input.value).join('');

    if (otp.length === 5) {
        fetch('/verify_otp', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ otp: otp })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                verificationSuccess.style.display = 'block';
                verificationSuccess.innerText = data.message;
                verificationSuccess.style.color = data.color || 'var(--neon)';
                setTimeout(() => {
                    emailVerification.style.display = 'none';
                    startTransfer();
                }, 1000);
            } else {
                verificationSuccess.style.display = 'block';
                verificationSuccess.innerText = data.message;
                verificationSuccess.style.color = data.color || 'var(--error-red)';

                if (data.reload) {
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                }
            }
        })
        .catch(error => {
            console.error('Error verifying OTP:', error);
            alert('Failed to verify OTP. Please try again.');
        });
    } else {
        alert('Please enter a valid 5-digit OTP.');
    }
});

document.body.appendChild(fileInput);