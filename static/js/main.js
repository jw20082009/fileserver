let uploadQueue = [];
let isUploading = false;

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.display = 'none';
    }, 2000);
}

function updateFileList() {
    const input = document.getElementById('video-input');
    const fileList = document.getElementById('selected-files');
    uploadQueue.push(...Array.from(input.files));
    
    fileList.innerHTML = '<h3>待上传文件：</h3>';
    uploadQueue.forEach((file, index) => {
        fileList.innerHTML += `
            <div class="queued-file">
                <span>${file.name}</span>
                <button onclick="removeFromQueue(${index})" class="button delete-button">移除</button>
            </div>`;
    });
    
    input.value = '';
    
    if (!isUploading && uploadQueue.length > 0) {
        uploadFiles();
    }
}

function removeFromQueue(index) {
    if (!isUploading || index !== 0) {
        uploadQueue.splice(index, 1);
        updateQueueDisplay();
    }
}

function updateQueueDisplay() {
    const fileList = document.getElementById('selected-files');
    if (uploadQueue.length === 0) {
        fileList.innerHTML = '';
        return;
    }
    
    fileList.innerHTML = '<h3>待上传文件：</h3>';
    uploadQueue.forEach((file, index) => {
        fileList.innerHTML += `
            <div class="queued-file">
                <span>${file.name}</span>
                <button onclick="removeFromQueue(${index})" class="button delete-button">移除</button>
            </div>`;
    });
}

function uploadFiles() {
    if (!isUploading && uploadQueue.length > 0) {
        isUploading = true;
        const progressBar = document.getElementById('progress-bar');
        progressBar.style.width = '0%';
        progressBar.style.backgroundColor = 'var(--primary-color)';
        uploadNextFile();
    }
    return false;
}

function uploadNextFile() {
    if (uploadQueue.length > 0) {
        const file = uploadQueue[0];
        const formData = new FormData();
        formData.append('video', file);
        
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/');
        
        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percent = (e.loaded / e.total) * 100;
                const progressBar = document.getElementById('progress-bar');
                const progressText = document.getElementById('progress-text');
                progressBar.style.width = percent + '%';
                progressText.textContent = `正在上传 ${file.name}: ${Math.round(percent)}%`;
            }
        };
        
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 303 || xhr.status === 200) {
                    uploadQueue.shift();
                    updateQueueDisplay();
                    const progressText = document.getElementById('progress-text');
                    
                    if (uploadQueue.length > 0) {
                        progressText.textContent = `${file.name} 上传完成，开始上传下一个文件...`;
                        setTimeout(uploadNextFile, 1000);
                    } else {
                        progressText.textContent = '所有文件上传完成！';
                        isUploading = false;
                    }
                    refreshVideoList();
                } else {
                    const progressText = document.getElementById('progress-text');
                    progressText.textContent = `${file.name} 上传失败`;
                    const progressBar = document.getElementById('progress-bar');
                    progressBar.style.backgroundColor = 'var(--danger-color)';
                    isUploading = false;
                }
            }
        };
        
        xhr.send(formData);
    }
}

function refreshVideoList() {
    fetch('/')
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newList = doc.querySelector('.video-list');
            const currentList = document.querySelector('.video-list');
            currentList.innerHTML = newList.innerHTML;
        });
}

function deleteFile(filename) {
    if (confirm('确定要删除 ' + filename + ' 吗？')) {
        fetch('/delete/' + encodeURIComponent(filename), {
            method: 'DELETE'
        }).then(response => {
            if (response.ok) {
                window.location.reload();
            } else {
                showToast('删除失败！');
            }
        });
    }
}

function copyVideoUrl(filename) {
    const url = window.location.origin + '/videos/' + filename;
    const tempInput = document.createElement('input');
    tempInput.style.position = 'absolute';
    tempInput.style.left = '-9999px';
    tempInput.value = url;
    document.body.appendChild(tempInput);
    
    tempInput.select();
    try {
        document.execCommand('copy');
        showToast('URL 复制成功！');
    } catch (err) {
        console.error('Failed to copy URL:', err);
        showToast('URL 复制失败');
    }
    
    document.body.removeChild(tempInput);
}