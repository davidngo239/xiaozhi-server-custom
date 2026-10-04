package xiaozhi.modules.device.dao;

import java.util.Date;

import org.apache.ibatis.annotations.Mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import xiaozhi.modules.device.entity.DeviceEntity;

@Mapper
public interface DeviceDao extends BaseMapper<DeviceEntity> {
    /**
     * Lấy thời gian kết nối cuối cùng của tất cả các thiết bị của đại lý này
     * 
     * @param agentId id đại lý
     * @return
     */
    Date getAllLastConnectedAtByAgentId(String agentId);

}