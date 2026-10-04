package xiaozhi.common.page;

import java.io.Serializable;
import java.util.List;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * Lớp công cụ phân trang
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Data
@Schema(description = "分页数据")
public class PageData<T> implements Serializable {
    @Schema(description = "总记录数")
    private int total;

    @Schema(description = "列表数据")
    private List<T> list;

    /**
     * Phân trang
     *
     * @param list Liệt kê dữ liệu
     * @param total Tổng số hồ sơ
     */
    public PageData(List<T> list, long total) {
        this.list = list;
        this.total = (int) total;
    }
}