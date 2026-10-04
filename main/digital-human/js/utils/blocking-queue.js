export default class BlockingQueue {
    #items   = [];
    #waiters = [];          // {resolve, reject, min, timer, onTimeout}

    /* Cổng một lần của hàng đợi trống */
    #emptyPromise = null;
    #emptyResolve = null;

    /* Nhà sản xuất: chèn dữ liệu */
    enqueue(item, ...restItems) {
        if (restItems.length === 0) {
            this.#items.push(item);
        }
        // Nếu được cung cấp thêm tham số, hãy xử lý hàng loạt tất cả các mục
        else {
            const items = [item, ...restItems].filter(i => i);
            if (items.length === 0) return;
            this.#items.push(...items);
        }
        // Nếu có một cổng xếp hàng trống, tất cả những người đang chờ sẽ được thả ngay lập tức
        if (this.#emptyResolve) {
            this.#emptyResolve();
            this.#emptyResolve = null;
            this.#emptyPromise = null;
        }

        // Đánh thức tất cả những người phục vụ đang chờ đợi
        this.#wakeWaiters();
    }

    /* Người tiêu dùng: thanh tối thiểu hoặc thời gian chờ ms tùy điều kiện nào đến trước */
    async dequeue(min = 1, timeout = Infinity, onTimeout = null) {
        // 1. Nếu trống, hãy đợi dữ liệu đầu tiên đến (tất cả các cuộc gọi đều có cùng một lời hứa)
        if (this.#items.length === 0) {
            await this.#waitForFirstItem();
        }

        // sự hài lòng ngay lập tức
        if (this.#items.length >= min) {
            return this.#flush();
        }

        // cần phải đợi
        return new Promise((resolve, reject) => {
            let timer = null;
            const waiter = { resolve, reject, min, onTimeout, timer };

            // logic thời gian chờ
            if (Number.isFinite(timeout)) {
                waiter.timer = setTimeout(() => {
                    this.#removeWaiter(waiter);
                    if (onTimeout) onTimeout(this.#items.length);
                    resolve(this.#flush());
                }, timeout);
            }

            this.#waiters.push(waiter);
        });
    }

    /* Trình tạo cổng hàng đợi trống */
    #waitForFirstItem() {
        if (!this.#emptyPromise) {
            this.#emptyPromise = new Promise(r => (this.#emptyResolve = r));
        }
        return this.#emptyPromise;
    }

    /* Nội bộ: Sau mỗi lần thay đổi dữ liệu, hãy kiểm tra xem người phục vụ nào đã hài lòng */
    #wakeWaiters() {
        for (let i = this.#waiters.length - 1; i >= 0; i--) {
            const w = this.#waiters[i];
            if (this.#items.length >= w.min) {
                this.#removeWaiter(w);
                w.resolve(this.#flush());
            }
        }
    }

    #removeWaiter(waiter) {
        const idx = this.#waiters.indexOf(waiter);
        if (idx !== -1) {
            this.#waiters.splice(idx, 1);
            if (waiter.timer) clearTimeout(waiter.timer);
        }
    }

    #flush() {
        const snapshot = [...this.#items];
        this.#items.length = 0;
        return snapshot;
    }

    /* Độ dài bộ đệm hiện tại (không bao gồm người phục vụ) */
    get length() {
        return this.#items.length;
    }

    /* Xóa hàng đợi (giữ tham chiếu Đối tượng, không ảnh hưởng đến người phục vụ) */
    clear() {
        this.#items.length = 0;
    }
}