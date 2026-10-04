// Phát hiện tải hình nền
(function() {
    const backgroundContainer = document.getElementById('backgroundContainer');

    // Trích xuất URL hình nền
    let bgImageUrl = window.getComputedStyle(backgroundContainer).backgroundImage;
    const urlMatch = bgImageUrl && bgImageUrl.match(/url\(["']?(.*?)["']?\)/);
    
    if (!urlMatch || !urlMatch[1]) {
        console.warn('Không tìm thấy URL ảnh nền hợp lệ.');
        return;
    }
    
    bgImageUrl = urlMatch[1];
    
    const bgImage = new Image();
    bgImage.onerror = function() {
        console.error('Tải ảnh nền thất bại:', bgImageUrl);
    };

    // Đang tải thành công hiển thị đang tải mô hình
    bgImage.onload = function() {
        modelLoading.style.display = 'flex';
    };

    bgImage.src = bgImageUrl;
})();
