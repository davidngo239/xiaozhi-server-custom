package xiaozhi.common.utils;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

import lombok.Data;

/**
 * Nút cây, tất cả những ai cần triển khai nút cây cần kế thừa lớp này
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Data
public class TreeNode<T> implements Serializable {

    /**
     * khóa chính
     */
    private Long id;
    /**
     * ID cấp trên
     */
    private Long pid;
    /**
     * Danh sách các nút con
     */
    private List<T> children = new ArrayList<>();

}