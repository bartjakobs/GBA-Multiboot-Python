import wiringpi as wiringpi
import time
import math 
import sys
def WriteSPI32(w): 
    buf = [0,0,0,0]
    buf[3] = (w & 0x000000ff)
    buf[2] = (w & 0x0000ff00) >> 8
    buf[1] = (w & 0x00ff0000) >> 16
    buf[0] = (w & 0xff000000) >> 24
    length, buf = wiringpi.wiringPiSPIDataRW(0, bytes(buf))
    r=0
    r += buf[0] << 24
    r += buf[1] << 16
    r += buf[2] << 8
    r += buf[3]
    return r


def WaitSPI32(w, comp): 
    r=-1
    while(r!=comp):
        r = WriteSPI32(w)
        time.sleep(0.01)


def getNext(fp):
    n = fp.read(1)
    if(len(n) == 0):
        return 0
    return n[0]
    

def main():
    filename = sys.argv[1]
    print("Filename "+filename)
    fp = open(filename,'rb')
    
    fp.seek(0,2)
    fsize = (fp.tell() + 0x0f) & 0xfffffff0
    print("fsize, ", fsize)
    if (fsize > 0x40000):
        print("Err: Max file size 256kB\n")
        return
    fp.seek(0)

    wiringpi.wiringPiSetupGpio()
    wiringpi.wiringPiSPISetup(0, 100000)
    print("Looking for Gameboy")
    WaitSPI32(0x00006202, 0x72026202) ## Look for gba

    print("Found GBA!")
    r = WriteSPI32(0x00006202)
    r = WriteSPI32(0x00006102)

    fcnt = 0

    print("Send Header");
    for i in range(0, 0x5f+1):
        
        w = fp.read(1)[0]
        w = fp.read(1)[0] << 8 | w
        fcnt += 2
        r = WriteSPI32(w)
    print("Sent!")
    
    r = WriteSPI32(0x00006200) ## Transfer comokete
    print("Exchange master/slave info again")
    r = WriteSPI32(0x00006202)
    print("Send palette data")
    r = WriteSPI32(0x000063d1)
    r = WriteSPI32(0x000063d1)
    
    m = ((r & 0x00ff0000) >> 8) + 0xffff00d1
    h = ((r & 0x00ff0000) >> 16) + 0xf
    print("Send handshake")
    r = WriteSPI32((((r >> 16) + 0xf) & 0xff) | 0x00006400)
    print("Send game length")
    r = WriteSPI32(int(math.ceil((fsize - 0x190) / 4)))

    f = (((r & 0x00ff0000) >> 8) + h) | 0xffff0000
    c = 0x0000c387
    
    print("Send encrypted data")

    while (fcnt < fsize):
        w = getNext(fp)
        w = getNext(fp) << 8 | w
        w = getNext(fp) << 16 | w
        w = getNext(fp) << 24 | w

        w2 = w
        for bit in range(0, 32):
            if ((c ^ w) & 0x01):
                c = (c >> 1) ^ 0x0000c37b
            else:
                c = c >> 1
            w = w >> 1
        
        w = w & 0xffffffff
        m = ((0xffffffff & (0x6f646573 * m)) + 1) 
        WriteSPI32(0xffffffff & (w2 ^ ((~(0x02000000 + fcnt)) + 1) ^ m ^ 0x43202f2f))
        fcnt = fcnt + 4
        
    
    print("Sent")
    fp.close()

    for bit in range(0, 32):
        if ((c ^ f) & 0x01):
            c = (c >> 1) ^ 0x0000c37b
        else:
            c = c >> 1
        f = f >> 1
    
    print("Wait for GBA to respond with CRC")
    WaitSPI32(0x00000065, 0x00750065)
    print("GBA ready with CRC, exchanging")
    r = WriteSPI32(0x00000066)
    r = WriteSPI32(c)

    print("CRC ...hope they match!")
    print("MulitBoot done")


    


main()