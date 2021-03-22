//
// --------------------------------------------------------------------------
// SharedMessagePort.m
// Created for Mac Mouse Fix (https://github.com/noah-nuebling/mac-mouse-fix)
// Created by Noah Nuebling in 2021
// Licensed under MIT
// --------------------------------------------------------------------------
//

#import "SharedMessagePort.h"
#import <Cocoa/Cocoa.h>
#import "Constants.h"

@implementation SharedMessagePort

+ (NSData *_Nullable)sendMessage:(NSString * _Nonnull)message withPayload:(NSObject <NSCoding> * _Nullable)payload expectingReply:(BOOL)replyExpected {
    
    NSDictionary *messageDict;
    if (payload) {
        messageDict = @{
            kMFMessageKeyMessage: message,
            kMFMessageKeyPayload: payload, // This crashes if payload is nil for some reason
        };
    } else {
        messageDict = @{
            kMFMessageKeyMessage: message,
        };
    }
    
    NSLog(@"Sending message: %@ with payload: %@ from bundle: %@ via message port", message, payload, NSBundle.mainBundle.bundleIdentifier);
    
    NSString *remotePortName;
    if ([NSBundle.mainBundle.bundleIdentifier isEqual:kMFBundleIDApp]) {
        remotePortName = @"com.nuebling.mousefix.helper.port";
    } else if ([NSBundle.mainBundle.bundleIdentifier isEqual:kMFBundleIDHelper]) {
        remotePortName = @"com.nuebling.mousefix.port";
    }
    
    CFMessagePortRef remotePort = CFMessagePortCreateRemote(kCFAllocatorDefault, (__bridge CFStringRef)remotePortName);
    if (remotePort == NULL) {
        NSLog(@"there is no CFMessagePort");
        return nil;
    }
    SInt32 messageID = 0x420666; // Arbitrary
    CFDataRef messageData = (__bridge CFDataRef)[NSKeyedArchiver archivedDataWithRootObject:messageDict];;
    CFTimeInterval sendTimeout = 0.0;
    CFTimeInterval recieveTimeout = 0.0;
    CFStringRef replyMode = NULL;
    CFDataRef returnData;
    if (replyExpected) {
        recieveTimeout = 0.1; // 1.0;
        replyMode = kCFRunLoopDefaultMode;
    }
    SInt32 status = CFMessagePortSendRequest(remotePort, messageID, messageData, sendTimeout, recieveTimeout, replyMode, &returnData);
    CFRelease(remotePort);
    if (status != 0) {
        NSLog(@"Non-zero CFMessagePortSendRequest status: %d", status);
    }
    
    NSData *returnDataNS = nil;
    if (replyExpected) {
        returnDataNS = (__bridge NSData *)returnData;
    }
    return returnDataNS;
}
//
//+ (CFDataRef _Nullable)sendMessage:(NSString *_Nonnull)message expectingReply:(BOOL)expectingReply {
//
//    NSLog(@"Sending message: %@ via message port from bundle: %@", message, NSBundle.mainBundle);
//
//    CFMessagePortRef remotePort = CFMessagePortCreateRemote(kCFAllocatorDefault, CFSTR("com.nuebling.mousefix.helper.port"));
//    if (remotePort == NULL) {
//        NSLog(@"There is no CFMessagePort");
//        return nil;
//    }
//
//    SInt32 messageID = 0x420666; // Arbitrary
//    CFDataRef messageData = (__bridge CFDataRef)[message dataUsingEncoding:kUnicodeUTF8Format];
//    CFTimeInterval sendTimeout = 0.0;
//    CFTimeInterval receiveTimeout = 0.0;
//    CFStringRef replyMode = NULL;
//    CFDataRef returnData;
//    if (expectingReply) {
//        receiveTimeout = 0.1; // 1.0
//        replyMode = kCFRunLoopDefaultMode;
//    }
//    SInt32 status = CFMessagePortSendRequest(remotePort, messageID, messageData, sendTimeout, receiveTimeout, replyMode, &returnData);
//    if (status != 0) {
//        NSLog(@"Non-zero CFMessagePortSendRequest status: %d", status);
//    }
//    CFRelease(remotePort);
//
//    return returnData;
//}

@end
