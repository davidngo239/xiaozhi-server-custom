package xiaozhi.modules.device.dao;

import java.util.List;

import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.device.entity.DeviceAddressBookEntity;

@Mapper
public interface DeviceAddressBookDao extends BaseMapper<DeviceAddressBookEntity> {

    /**
     * Thêm bản ghi sổ địa chỉ thiết bị
     */
    int insertAddressBook(DeviceAddressBookEntity entity);

    /**
     * Lấy danh sách sổ địa chỉ thiết bị
     */
    List<DeviceAddressBookEntity> getAddressBookList(@Param("macAddress") String macAddress);

    /**
     * Cập nhật bí danh
     */
    void updateAlias(@Param("macAddress") String macAddress, @Param("targetMac") String targetMac, @Param("alias") String alias);

    /**
     * Cập nhật quyền
     */
    void updatePermission(@Param("macAddress") String macAddress, @Param("targetMac") String targetMac, @Param("hasPermission") Boolean hasPermission);

    /**
     * Xóa hàng loạt bản ghi sổ địa chỉ liên quan đến thiết bị
     */
    void deleteByMacAddresses(@Param("macAddresses") List<String> macAddresses);
}
