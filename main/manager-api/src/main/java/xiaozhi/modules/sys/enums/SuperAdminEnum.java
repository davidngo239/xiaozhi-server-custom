package xiaozhi.modules.sys.enums;

/**
 * Bảng liệt kê siêu quản trị viên
 */
public enum SuperAdminEnum {
    YES(1),
    NO(0);

    private int value;

    SuperAdminEnum(int value) {
        this.value = value;
    }

    public int value() {
        return this.value;
    }
}