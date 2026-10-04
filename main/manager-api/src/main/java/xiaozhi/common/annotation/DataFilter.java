package xiaozhi.common.annotation;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Chú thích lọc dữ liệu
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DataFilter {
    /**
     * bí danh bảng
     */
    String tableAlias() default "";

    /**
     * ID người dùng
     */
    String userId() default "creator";

    /**
     * ID bộ phận
     */
    String deptId() default "dept_id";

}