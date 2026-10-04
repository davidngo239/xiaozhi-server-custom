package xiaozhi.common.interceptor;

/**
 * phạm vi dữ liệu
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
public class DataScope {
    private String sqlFilter;

    public DataScope(String sqlFilter) {
        this.sqlFilter = sqlFilter;
    }

    public String getSqlFilter() {
        return sqlFilter;
    }

    public void setSqlFilter(String sqlFilter) {
        this.sqlFilter = sqlFilter;
    }

    @Override
    public String toString() {
        return this.sqlFilter;
    }
}