package xiaozhi.common.handler;

import java.util.Date;

import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;

import xiaozhi.common.constant.Constant;
import xiaozhi.common.user.UserDetail;
import xiaozhi.modules.security.user.SecurityUser;

/**
 * Các trường công khai, giá trị tự động điền
 * Bản quyền (c) Renren Kaiyuan Mọi quyền được bảo lưu.
 * Website: https://www.renren.io
 */
@Component
public class FieldMetaObjectHandler implements MetaObjectHandler {
    private final static String CREATE_DATE = "createDate";
    private final static String CREATOR = "creator";
    private final static String UPDATE_DATE = "updateDate";
    private final static String UPDATER = "updater";

    private final static String DATA_OPERATION = "dataOperation";

    @Override
    public void insertFill(MetaObject metaObject) {
        UserDetail user = SecurityUser.getUser();
        Date date = new Date();

        // Người sáng tạo
        strictInsertFill(metaObject, CREATOR, Long.class, user.getId());
        // Thời gian tạo - hỗ trợ hai tên trường: createDate và createAt
        if (metaObject.hasSetter(CREATE_DATE)) {
            strictInsertFill(metaObject, CREATE_DATE, Date.class, date);
        }
        if (metaObject.hasSetter("createdAt")) {
            strictInsertFill(metaObject, "createdAt", Date.class, date);
        }

        // Trình cập nhật
        strictInsertFill(metaObject, UPDATER, Long.class, user.getId());
        // Thời gian cập nhật - hỗ trợ hai tên trường:updateDate vàupdateAt
        if (metaObject.hasSetter(UPDATE_DATE)) {
            strictInsertFill(metaObject, UPDATE_DATE, Date.class, date);
        }
        if (metaObject.hasSetter("updatedAt")) {
            strictInsertFill(metaObject, "updatedAt", Date.class, date);
        }

        // Nhận dạng dữ liệu
        strictInsertFill(metaObject, DATA_OPERATION, String.class, Constant.DataOperation.INSERT.getValue());
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        Date date = new Date();

        // Trình cập nhật
        strictUpdateFill(metaObject, UPDATER, Long.class, SecurityUser.getUserId());
        // Thời gian cập nhật - hỗ trợ hai tên trường:updateDate vàupdateAt
        if (metaObject.hasSetter(UPDATE_DATE)) {
            strictUpdateFill(metaObject, UPDATE_DATE, Date.class, date);
        }
        if (metaObject.hasSetter("updatedAt")) {
            strictUpdateFill(metaObject, "updatedAt", Date.class, date);
        }

        // Nhận dạng dữ liệu
        strictInsertFill(metaObject, DATA_OPERATION, String.class, Constant.DataOperation.UPDATE.getValue());
    }
}