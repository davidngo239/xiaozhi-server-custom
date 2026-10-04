package xiaozhi.common.utils;

import lombok.Data;
/**
 * Đối tượng đặc tả định dạng JSON-RPC2.0
 */
@Data
public class JsonRpcTwo {
    private String jsonrpc = "2.0";
    private String method;
    private Object params;
    private Integer id;

    public JsonRpcTwo(String method, Object params, Integer id) {
        this.method = method;
        this.params = params;
        this.id = id;
    }


}