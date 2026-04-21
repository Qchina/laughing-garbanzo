package demo;

/**
 * 演示类
 */
public class DemoClass {
    private int id;
    private String name;
    private static int count = 0;
    
    public DemoClass(int id, String name) {
        this.id = id;
        this.name = name;
        count++;
    }
    
    public int getId() {
        return id;
    }
    
    public void setId(int id) {
        this.id = id;
    }
    
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public static int getCount() {
        return count;
    }
    
    public boolean validate() {
        if (id <= 0) {
            return false;
        }
        if (name == null || name.isEmpty()) {
            return false;
        }
        return true;
    }
    
    public void processData(int[] data) {
        for (int i = 0; i < data.length; i++) {
            if (data[i] > 0) {
                System.out.println("Positive: " + data[i]);
            } else if (data[i] < 0) {
                System.out.println("Negative: " + data[i]);
            } else {
                System.out.println("Zero: " + data[i]);
            }
        }
    }
    
    public String formatInfo() {
        return "DemoClass{id=" + id + ", name='" + name + "'}";
    }
}