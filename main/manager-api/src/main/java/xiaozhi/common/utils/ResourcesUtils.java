package xiaozhi.common.utils;

import lombok.AllArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ResourceLoader;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Component;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.exception.ErrorCode;


import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

/**
 * Công cụ xử lý tài nguyên
 */
@AllArgsConstructor
@Slf4j
@Component
public class ResourcesUtils {
    private ResourceLoader resourceLoader;

    /**
     * Đọc tài nguyên và trả về một chuỗi
     * @param fileName đường dẫn tài nguyên: bắt đầu dưới tài nguyên
     * @return chuỗi
     */
    public String loadString(String fileName)  {
        Resource resource = resourceLoader.getResource("classpath:" + fileName);
        StringBuilder luaScriptBuilder = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                luaScriptBuilder.append(line).append("\n");
            }
        }  catch (IOException e){
            log.error("方法：loadString()读取资源失败--{}",e.getMessage());
            throw new RenException(ErrorCode.RESOURCE_READ_ERROR);
        }
        return luaScriptBuilder.toString();
    }
}
